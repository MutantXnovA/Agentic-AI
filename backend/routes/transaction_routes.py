from flask import Blueprint, request, jsonify
from auth import require_auth
from database import get_db

txn_bp = Blueprint('transactions', __name__, url_prefix='/api/transactions')

@txn_bp.route('', methods=['GET'])
@require_auth
def get_transactions():
    """
    Search, filter, sort, and paginate transactions.
    Supports global search across ID, reference, UTR, counterparty, description, amount.
    Filter by source, entity, account, currency, match status.
    """
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 25))
    offset = (page - 1) * limit
    
    search = request.args.get('search', '').strip()
    source_id = request.args.get('source_id')
    status = request.args.get('status')
    currency = request.args.get('currency')
    entity_id = request.args.get('entity_id')
    account_id = request.args.get('account_id')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    sort_by = request.args.get('sort_by', 'id')
    sort_order = request.args.get('sort_order', 'DESC').upper()
    
    allowed_sort_fields = ['id', 'txn_date', 'amount', 'external_txn_id', 'ref_number', 'status']
    if sort_by not in allowed_sort_fields:
        sort_by = 'id'
        
    conn = get_db()
    cursor = conn.cursor()
    
    where_clauses = ["1=1"]
    params = []
    
    if search:
        where_clauses.append("(t.external_txn_id LIKE ? OR t.ref_number LIKE ? OR t.description LIKE ? OR t.counterparty LIKE ? OR t.amount LIKE ?)")
        search_pattern = f"%{search}%"
        params.extend([search_pattern] * 5)
        
    if source_id:
        where_clauses.append("t.source_id = ?")
        params.append(source_id)
        
    if status:
        where_clauses.append("t.status = ?")
        params.append(status)
        
    if currency:
        where_clauses.append("t.currency = ?")
        params.append(currency)
        
    if entity_id:
        where_clauses.append("t.entity_id = ?")
        params.append(entity_id)

    if account_id:
        where_clauses.append("t.account_id = ?")
        params.append(account_id)
        
    if date_from:
        where_clauses.append("t.txn_date >= ?")
        params.append(date_from)
        
    if date_to:
        where_clauses.append("t.txn_date <= ?")
        params.append(date_to)

    where_sql = " AND ".join(where_clauses)

    # Count total matching records
    cursor.execute(f"SELECT COUNT(*) as total FROM transactions t WHERE {where_sql}", params)
    total_records = cursor.fetchone()['total']

    # Fetch paginated dataset with joins
    query = f"""
        SELECT t.*, s.name as source_name, s.code as source_code,
               a.account_name, e.name as entity_name,
               e.exc_id, e.exc_code, e.exc_status, e.exc_priority
        FROM transactions t
        LEFT JOIN transaction_sources s ON t.source_id = s.id
        LEFT JOIN accounts a ON t.account_id = a.id
        LEFT JOIN entities e ON t.entity_id = e.id
        LEFT JOIN (
            SELECT id as exc_id, exception_code as exc_code, transaction_id, status as exc_status, priority as exc_priority
            FROM exceptions
        ) e ON t.id = e.transaction_id
        WHERE {where_sql}
        ORDER BY t.{sort_by} {sort_order}
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    cursor.execute(query, params)
    transactions = [dict(row) for row in cursor.fetchall()]

    conn.close()
    
    return jsonify({
        'transactions': transactions,
        'pagination': {
            'total': total_records,
            'page': page,
            'limit': limit,
            'total_pages': (total_records + limit - 1) // limit
        }
    })

@txn_bp.route('/<int:txn_id>/compare', methods=['GET'])
@require_auth
def get_transaction_side_by_side(txn_id):
    """
    Returns complete side-by-side details comparing Source A and Source B records with exact diff calculations.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Fetch primary transaction
    cursor.execute("""
        SELECT t.*, s.name as source_name, a.account_name, e.name as entity_name
        FROM transactions t
        LEFT JOIN transaction_sources s ON t.source_id = s.id
        LEFT JOIN accounts a ON t.account_id = a.id
        LEFT JOIN entities e ON t.entity_id = e.id
        WHERE t.id = ?
    """, (txn_id,))
    txn_a = cursor.fetchone()
    
    if not txn_a:
        conn.close()
        return jsonify({'error': 'Transaction not found'}), 404
        
    txn_a_dict = dict(txn_a)
    
    # 2. Find matching reconciliation result if exists
    cursor.execute("""
        SELECT r.*, r2.rule_name, e.id as exception_id, e.exception_code, e.status as exc_status, e.priority as exc_priority
        FROM reconciliation_results r
        LEFT JOIN reconciliation_rules r2 ON r.matched_rule_id = r2.id
        LEFT JOIN exceptions e ON r.id = e.recon_result_id
        WHERE r.source_a_id = ? OR r.source_b_id = ?
        ORDER BY r.id DESC LIMIT 1
    """, (txn_id, txn_id))
    recon_res = cursor.fetchone()
    
    txn_b_dict = None
    diff_analysis = {}
    
    if recon_res:
        recon_dict = dict(recon_res)
        other_txn_id = recon_dict['source_b_id'] if recon_dict['source_a_id'] == txn_id else recon_dict['source_a_id']
        
        if other_txn_id:
            cursor.execute("""
                SELECT t.*, s.name as source_name, a.account_name, e.name as entity_name
                FROM transactions t
                LEFT JOIN transaction_sources s ON t.source_id = s.id
                LEFT JOIN accounts a ON t.account_id = a.id
                LEFT JOIN entities e ON t.entity_id = e.id
                WHERE t.id = ?
            """, (other_txn_id,))
            txn_b = cursor.fetchone()
            if txn_b:
                txn_b_dict = dict(txn_b)
                
                # Compute difference breakdown
                diff_analysis = {
                    'amount_diff': abs(txn_a_dict['amount'] - txn_b_dict['amount']),
                    'amount_match': txn_a_dict['amount'] == txn_b_dict['amount'],
                    'currency_match': txn_a_dict['currency'] == txn_b_dict['currency'],
                    'ref_match': (txn_a_dict.get('ref_number') or '') == (txn_b_dict.get('ref_number') or ''),
                    'date_diff_days': recon_dict.get('date_diff_days', 0),
                    'match_score': recon_dict.get('match_score', 0),
                    'matched_rule_name': recon_dict.get('rule_name', 'Manual / System Match')
                }

    conn.close()
    
    return jsonify({
        'source_a': txn_a_dict,
        'source_b': txn_b_dict,
        'reconciliation_result': dict(recon_res) if recon_res else None,
        'diff_analysis': diff_analysis
    })
