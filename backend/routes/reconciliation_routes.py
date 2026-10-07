from flask import Blueprint, request, jsonify, g
from auth import require_auth, require_role
from database import get_db
from reconciliation_engine import run_reconciliation
from audit import log_audit_event
from config import Config

recon_bp = Blueprint('reconciliation', __name__, url_prefix='/api/reconciliation')

@recon_bp.route('/run', methods=['POST'])
@require_auth
@require_role([Config.ROLE_SUPER_ADMIN, Config.ROLE_FINANCE_ADMIN, Config.ROLE_FINANCE_MANAGER, Config.ROLE_RECON_ANALYST])
def trigger_reconciliation():
    """
    Triggers automated multi-pass reconciliation engine.
    """
    data = request.json or {}
    source_a_id = data.get('source_a_id')
    source_b_id = data.get('source_b_id')
    
    try:
        summary = run_reconciliation(user_id=g.current_user['id'], source_a_id=source_a_id, source_b_id=source_b_id)
        return jsonify({
            'message': 'Reconciliation run completed successfully',
            'summary': summary
        })
    except Exception as e:
        return jsonify({'error': f'Reconciliation execution failed: {str(e)}'}), 500

@recon_bp.route('/runs', methods=['GET'])
@require_auth
def get_reconciliation_runs():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.*, u.username as initiated_by_user
        FROM reconciliation_runs r
        LEFT JOIN users u ON r.initiated_by = u.id
        ORDER BY r.id DESC LIMIT 50
    """)
    runs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'runs': runs})

@recon_bp.route('/results', methods=['GET'])
@require_auth
def get_reconciliation_results():
    run_id = request.args.get('run_id')
    match_status = request.args.get('match_status')
    
    conn = get_db()
    cursor = conn.cursor()
    
    where = ["1=1"]
    params = []
    
    if run_id:
        where.append("r.run_id = ?")
        params.append(run_id)
    if match_status:
        where.append("r.match_status = ?")
        params.append(match_status)
        
    query = f"""
        SELECT r.*, 
               ta.external_txn_id as source_a_ext_id, ta.amount as source_a_amount, ta.currency as source_a_curr, ta.counterparty as source_a_cp, ta.txn_date as source_a_date,
               tb.external_txn_id as source_b_ext_id, tb.amount as source_b_amount, tb.currency as source_b_curr, tb.counterparty as source_b_cp, tb.txn_date as source_b_date,
               ru.rule_name, e.id as exception_id, e.exception_code, e.status as exc_status
        FROM reconciliation_results r
        LEFT JOIN transactions ta ON r.source_a_id = ta.id
        LEFT JOIN transactions tb ON r.source_b_id = tb.id
        LEFT JOIN reconciliation_rules ru ON r.matched_rule_id = ru.id
        LEFT JOIN exceptions e ON r.id = e.recon_result_id
        WHERE {" AND ".join(where)}
        ORDER BY r.id DESC LIMIT 100
    """
    cursor.execute(query, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'results': results})

@recon_bp.route('/manual-match', methods=['POST'])
@require_auth
@require_role([Config.ROLE_SUPER_ADMIN, Config.ROLE_FINANCE_ADMIN, Config.ROLE_FINANCE_MANAGER, Config.ROLE_RECON_ANALYST])
def manual_match_transactions():
    """
    Allows analysts/managers to manually pair two unmatched transactions.
    """
    data = request.json or {}
    source_a_id = data.get('source_a_id')
    source_b_id = data.get('source_b_id')
    reason = data.get('reason', 'Manual match verified by analyst')
    
    if not source_a_id or not source_b_id:
        return jsonify({'error': 'Both Source A and Source B transaction IDs are required.'}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM transactions WHERE id IN (?, ?)", (source_a_id, source_b_id))
    txns = cursor.fetchall()
    if len(txns) < 2:
        conn.close()
        return jsonify({'error': 'One or both transaction records were not found.'}), 404
        
    # Insert reconciliation result
    cursor.execute("""
        INSERT INTO reconciliation_results (run_id, source_a_id, source_b_id, match_status, match_score, notes)
        VALUES (1, ?, ?, 'Manual Match', 100.0, ?)
    """, (source_a_id, source_b_id, reason))
    recon_res_id = cursor.lastrowid
    
    # Update transactions as matched
    cursor.execute("UPDATE transactions SET is_matched = 1, status = 'Manual Match' WHERE id IN (?, ?)", (source_a_id, source_b_id))
    
    # Close any open exceptions associated with these transactions
    cursor.execute("""
        UPDATE exceptions 
        SET status = 'Resolved', resolution_summary = ?, closed_at = CURRENT_TIMESTAMP, closed_by = ?
        WHERE transaction_id IN (?, ?) AND status NOT IN ('Closed', 'Resolved')
    """, (f"Manually matched: {reason}", g.current_user['id'], source_a_id, source_b_id))

    conn.commit()
    conn.close()
    
    log_audit_event(
        action='MANUAL_TRANSACTION_MATCH',
        entity='reconciliation_results',
        record_id=str(recon_res_id),
        new_value={'source_a_id': source_a_id, 'source_b_id': source_b_id, 'reason': reason}
    )
    
    return jsonify({'message': 'Transactions successfully manually matched.'})
