import json
import uuid
from datetime import datetime
from database import get_db
from rule_engine import evaluate_pair
from exception_engine import create_exception_for_discrepancy
from audit import log_audit_event

def run_reconciliation(user_id: int, source_a_id: int = None, source_b_id: int = None) -> dict:
    """
    Executes multi-pass reconciliation engine comparing unmatched transactions.
    Creates reconciliation_runs, reconciliation_results, and auto-generates exceptions for discrepancies.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Fetch active rules ordered by priority ascending (Rule 1 highest priority)
    cursor.execute("""
        SELECT * FROM reconciliation_rules 
        WHERE is_active = 1 
        ORDER BY priority ASC
    """)
    rules = [dict(row) for row in cursor.fetchall()]
    
    # 2. Fetch unmatched transactions
    query_a = "SELECT * FROM transactions WHERE is_matched = 0"
    params_a = []
    if source_a_id:
        query_a += " AND source_id = ?"
        params_a.append(source_a_id)
        
    cursor.execute(query_a, params_a)
    txns_a = [dict(row) for row in cursor.fetchall()]
    
    query_b = "SELECT * FROM transactions WHERE is_matched = 0"
    params_b = []
    if source_b_id:
        query_b += " AND source_id = ?"
        params_b.append(source_b_id)
        
    cursor.execute(query_b, params_b)
    txns_b = [dict(row) for row in cursor.fetchall()]

    # If source_a_id and source_b_id were not specified, split pool into two distinct source types
    if not source_a_id and not source_b_id and txns_a:
        sources = list(set([t['source_id'] for t in txns_a]))
        if len(sources) >= 2:
            s_a = sources[0]
            s_b = sources[1]
            txns_a = [t for t in txns_a if t['source_id'] == s_a]
            txns_b = [t for t in txns_b if t['source_id'] == s_b]

    # Create Reconciliation Run Record
    run_code = f"RUN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
    cursor.execute("""
        INSERT INTO reconciliation_runs (run_code, initiated_by, started_at, total_processed, status)
        VALUES (?, ?, CURRENT_TIMESTAMP, ?, 'Processing')
    """, (run_code, user_id, len(txns_a) + len(txns_b)))
    run_id = cursor.lastrowid
    conn.commit()

    matched_a_ids = set()
    matched_b_ids = set()
    matched_count = 0
    partial_count = 0
    unmatched_count = 0
    exceptions_created = 0

    results_to_insert = []

    # 3. Execute Multi-pass matching rules
    for rule in rules:
        for t_a in txns_a:
            if t_a['id'] in matched_a_ids:
                continue
            for t_b in txns_b:
                if t_b['id'] in matched_b_ids:
                    continue
                    
                is_match, score, diff_details = evaluate_pair(t_a, t_b, rule)
                if is_match:
                    matched_a_ids.add(t_a['id'])
                    matched_b_ids.add(t_b['id'])
                    
                    status = 'Matched'
                    if diff_details['amount_diff'] > 0:
                        status = 'Amount Mismatch'
                    elif diff_details['date_diff_days'] > 0:
                        status = 'Date Mismatch'
                        
                    results_to_insert.append({
                        'run_id': run_id,
                        'source_a_id': t_a['id'],
                        'source_b_id': t_b['id'],
                        'match_status': status,
                        'matched_rule_id': rule['id'],
                        'match_score': score,
                        'amount_diff': diff_details['amount_diff'],
                        'date_diff_days': diff_details['date_diff_days'],
                        'txn_a': t_a,
                        'txn_b': t_b
                    })
                    if status == 'Matched':
                        matched_count += 1
                    else:
                        partial_count += 1
                    break

    # 4. Insert matched / mismatched reconciliation results and update transaction records
    for res in results_to_insert:
        cursor.execute("""
            INSERT INTO reconciliation_results (run_id, source_a_id, source_b_id, match_status, matched_rule_id, match_score, amount_diff, date_diff_days)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (res['run_id'], res['source_a_id'], res['source_b_id'], res['match_status'], res['matched_rule_id'], res['match_score'], res['amount_diff'], res['date_diff_days']))
        recon_res_id = cursor.lastrowid

        # Update transactions status
        is_fully_matched = 1 if res['match_status'] == 'Matched' else 0
        cursor.execute("UPDATE transactions SET is_matched = ?, status = ? WHERE id IN (?, ?)", 
                       (is_fully_matched, res['match_status'], res['source_a_id'], res['source_b_id']))
                       
        # Auto-create exception if amount mismatch or date mismatch
        if res['match_status'] in ['Amount Mismatch', 'Date Mismatch']:
            exc_type = 'Amount Mismatch' if res['match_status'] == 'Amount Mismatch' else 'Date Mismatch'
            create_exception_for_discrepancy(
                conn=conn,
                txn_id=res['source_a_id'],
                recon_res_id=recon_res_id,
                exc_type=exc_type,
                amount=res['amount_diff'],
                currency=res['txn_a']['currency'],
                description=f"{exc_type}: Source A amount {res['txn_a']['amount']} {res['txn_a']['currency']} vs Source B amount {res['txn_b']['amount']} {res['txn_b']['currency']} (Diff: {res['amount_diff']})"
            )
            exceptions_created += 1

    # 5. Handle remaining unmatched transactions in Source A and Source B
    unmatched_a = [t for t in txns_a if t['id'] not in matched_a_ids]
    unmatched_b = [t for t in txns_b if t['id'] not in matched_b_ids]
    
    for t_un in unmatched_a:
        cursor.execute("""
            INSERT INTO reconciliation_results (run_id, source_a_id, source_b_id, match_status, match_score, amount_diff)
            VALUES (?, ?, NULL, 'Missing in Source B', 0.0, ?)
        """, (run_id, t_un['id'], t_un['amount']))
        recon_res_id = cursor.lastrowid
        cursor.execute("UPDATE transactions SET status = 'Unmatched' WHERE id = ?", (t_un['id'],))
        
        # Create Exception for Unmatched Transaction
        create_exception_for_discrepancy(
            conn=conn,
            txn_id=t_un['id'],
            recon_res_id=recon_res_id,
            exc_type='Missing Transaction',
            amount=t_un['amount'],
            currency=t_un['currency'],
            description=f"Transaction {t_un['external_txn_id']} present in Source A but missing in Source B."
        )
        unmatched_count += 1
        exceptions_created += 1

    for t_un in unmatched_b:
        cursor.execute("""
            INSERT INTO reconciliation_results (run_id, source_a_id, source_b_id, match_status, match_score, amount_diff)
            VALUES (?, ?, NULL, 'Missing in Source A', 0.0, ?)
        """, (run_id, t_un['id'], t_un['amount']))
        recon_res_id = cursor.lastrowid
        cursor.execute("UPDATE transactions SET status = 'Unmatched' WHERE id = ?", (t_un['id'],))
        
        create_exception_for_discrepancy(
            conn=conn,
            txn_id=t_un['id'],
            recon_res_id=recon_res_id,
            exc_type='Missing Transaction',
            amount=t_un['amount'],
            currency=t_un['currency'],
            description=f"Transaction {t_un['external_txn_id']} present in Source B but missing in Source A."
        )
        unmatched_count += 1
        exceptions_created += 1

    # Update Reconciliation Run Record
    cursor.execute("""
        UPDATE reconciliation_runs 
        SET completed_at = CURRENT_TIMESTAMP, 
            matched_count = ?, 
            unmatched_count = ?, 
            partial_count = ?, 
            exceptions_created = ?, 
            status = 'Completed'
        WHERE id = ?
    """, (matched_count, unmatched_count, partial_count, exceptions_created, run_id))
    
    conn.commit()
    conn.close()

    log_audit_event(
        action='EXECUTE_RECONCILIATION',
        entity='reconciliation_runs',
        record_id=str(run_id),
        new_value={
            'run_code': run_code,
            'matched': matched_count,
            'unmatched': unmatched_count,
            'exceptions_created': exceptions_created
        }
    )

    return {
        'run_id': run_id,
        'run_code': run_code,
        'matched_count': matched_count,
        'partial_count': partial_count,
        'unmatched_count': unmatched_count,
        'exceptions_created': exceptions_created
    }
