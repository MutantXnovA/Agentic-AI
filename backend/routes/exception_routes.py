from flask import Blueprint, request, jsonify, g
from auth import require_auth, require_role
from database import get_db
from exception_engine import update_sla_statuses, get_ageing_bucket
from ai_assistant import analyze_exception_root_cause
from audit import log_audit_event
from config import Config

exception_bp = Blueprint('exceptions', __name__, url_prefix='/api/exceptions')

@exception_bp.route('', methods=['GET'])
@require_auth
def get_exceptions():
    """
    List, filter, and paginate exceptions.
    Quick filters: my_exceptions, critical, high_priority, sla_breached, due_today, unassigned, pending_approval.
    """
    update_sla_statuses() # Recalculate SLA statuses
    
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 25))
    offset = (page - 1) * limit
    
    quick_filter = request.args.get('filter')
    status = request.args.get('status')
    priority = request.args.get('priority')
    search = request.args.get('search', '').strip()
    
    conn = get_db()
    cursor = conn.cursor()
    
    where = ["1=1"]
    params = []
    
    if quick_filter == 'my_exceptions':
        where.append("e.owner_id = ?")
        params.append(g.current_user['id'])
    elif quick_filter == 'critical':
        where.append("e.priority = 'Critical'")
    elif quick_filter == 'high_priority':
        where.append("e.priority IN ('Critical', 'High')")
    elif quick_filter == 'sla_breached':
        where.append("e.sla_status = 'SLA Breached'")
    elif quick_filter == 'unassigned':
        where.append("e.owner_id IS NULL")
    elif quick_filter == 'pending_approval':
        where.append("e.approval_status = 'Pending Approval'")

    if status:
        where.append("e.status = ?")
        params.append(status)
        
    if priority:
        where.append("e.priority = ?")
        params.append(priority)
        
    if search:
        where.append("(e.exception_code LIKE ? OR e.description LIKE ? OR t.external_txn_id LIKE ? OR t.counterparty LIKE ?)")
        s_pat = f"%{search}%"
        params.extend([s_pat] * 4)

    where_sql = " AND ".join(where)

    cursor.execute(f"SELECT COUNT(*) as total FROM exceptions e LEFT JOIN transactions t ON e.transaction_id = t.id WHERE {where_sql}", params)
    total_records = cursor.fetchone()['total']

    query = f"""
        SELECT e.*, 
               u.full_name as owner_name, u.username as owner_username,
               t.external_txn_id, t.ref_number, t.txn_date, t.counterparty, t.amount as txn_amount,
               r.match_status
        FROM exceptions e
        LEFT JOIN users u ON e.owner_id = u.id
        LEFT JOIN transactions t ON e.transaction_id = t.id
        LEFT JOIN reconciliation_results r ON e.recon_result_id = r.id
        WHERE {where_sql}
        ORDER BY CASE e.priority 
            WHEN 'Critical' THEN 1 
            WHEN 'High' THEN 2 
            WHEN 'Medium' THEN 3 
            ELSE 4 END, e.id DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    cursor.execute(query, params)
    exceptions = []
    for row in cursor.fetchall():
        item = dict(row)
        item['ageing_bucket'] = get_ageing_bucket(item.get('ageing_days', 0))
        exceptions.append(item)

    conn.close()
    return jsonify({
        'exceptions': exceptions,
        'pagination': {
            'total': total_records,
            'page': page,
            'limit': limit,
            'total_pages': (total_records + limit - 1) // limit
        }
    })

@exception_bp.route('/<int:exc_id>', methods=['GET'])
@require_auth
def get_exception_detail(exc_id):
    """
    Fetch full detail for exception view drawer, including activity timeline, comments, AI suggestions.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT e.*, 
               u.full_name as owner_name, u.email as owner_email,
               t.external_txn_id, t.ref_number, t.txn_date, t.amount as txn_amount, t.currency as txn_currency, t.counterparty, t.description as txn_desc,
               s.name as source_name
        FROM exceptions e
        LEFT JOIN users u ON e.owner_id = u.id
        LEFT JOIN transactions t ON e.transaction_id = t.id
        LEFT JOIN transaction_sources s ON t.source_id = s.id
        WHERE e.id = ?
    """, (exc_id,))
    exc = cursor.fetchone()
    
    if not exc:
        conn.close()
        return jsonify({'error': 'Exception record not found'}), 404
        
    exc_dict = dict(exc)
    exc_dict['ageing_bucket'] = get_ageing_bucket(exc_dict.get('ageing_days', 0))

    # Fetch comments
    cursor.execute("""
        SELECT c.*, u.full_name as user_name, u.role as user_role
        FROM exception_comments c
        LEFT JOIN users u ON c.user_id = u.id
        WHERE c.exception_id = ?
        ORDER BY c.id ASC
    """, (exc_id,))
    comments = [dict(row) for row in cursor.fetchall()]

    # Fetch AI Root Cause Recommendation
    ai_recommendation = analyze_exception_root_cause(
        exc_type=exc_dict['exception_type'],
        description=exc_dict['description'],
        amount=exc_dict['amount']
    )

    conn.close()
    return jsonify({
        'exception': exc_dict,
        'comments': comments,
        'ai_recommendation': ai_recommendation
    })

@exception_bp.route('/<int:exc_id>/assign', methods=['PUT'])
@require_auth
@require_role([Config.ROLE_SUPER_ADMIN, Config.ROLE_FINANCE_ADMIN, Config.ROLE_FINANCE_MANAGER])
def reassign_exception(exc_id):
    data = request.json or {}
    new_owner_id = data.get('owner_id')
    reason = data.get('reason', 'Reassigned by manager')
    
    if not new_owner_id:
        return jsonify({'error': 'New owner ID is required.'}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT owner_id FROM exceptions WHERE id = ?", (exc_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        return jsonify({'error': 'Exception not found'}), 404
        
    prev_owner_id = existing['owner_id']
    cursor.execute("UPDATE exceptions SET owner_id = ? WHERE id = ?", (new_owner_id, exc_id))
    
    cursor.execute("""
        INSERT INTO exception_assignments (exception_id, previous_owner_id, new_owner_id, assigned_by, reason)
        VALUES (?, ?, ?, ?, ?)
    """, (exc_id, prev_owner_id, new_owner_id, g.current_user['id'], reason))

    conn.commit()
    conn.close()
    
    log_audit_event(action='REASSIGN_EXCEPTION', entity='exceptions', record_id=str(exc_id), new_value={'new_owner_id': new_owner_id, 'reason': reason})
    return jsonify({'message': 'Exception reassigned successfully'})

@exception_bp.route('/<int:exc_id>/status', methods=['PUT'])
@require_auth
def update_exception_status(exc_id):
    """
    Updates Exception state workflow.
    High value (>= $5,000) or Critical priority requires Manager Approval before transitioning to Resolved.
    """
    data = request.json or {}
    new_status = data.get('status')
    resolution_summary = data.get('resolution_summary', '')
    root_cause = data.get('root_cause', '')
    
    if not new_status:
        return jsonify({'error': 'Status is required.'}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM exceptions WHERE id = ?", (exc_id,))
    exc = cursor.fetchone()
    if not exc:
        conn.close()
        return jsonify({'error': 'Exception not found'}), 404
        
    exc_dict = dict(exc)
    
    # Check Manager Approval Requirement
    requires_approval = (exc_dict['priority'] == 'Critical' or exc_dict['amount'] >= 5000.0)
    
    if new_status in ['Resolved', 'Closed'] and requires_approval and g.current_user['role'] not in [Config.ROLE_SUPER_ADMIN, Config.ROLE_FINANCE_ADMIN, Config.ROLE_FINANCE_MANAGER]:
        # Switch to Pending Approval instead of direct resolution
        cursor.execute("""
            UPDATE exceptions 
            SET status = 'Pending Approval', approval_status = 'Pending Approval', root_cause = ?, resolution_summary = ?
            WHERE id = ?
        """, (root_cause, resolution_summary, exc_id))
        
        cursor.execute("""
            INSERT INTO approvals (exception_id, requested_by, proposed_resolution, status, comments)
            VALUES (?, ?, ?, 'Pending Approval', ?)
        """, (exc_id, g.current_user['id'], resolution_summary, f"Root cause: {root_cause}"))
        
        conn.commit()
        conn.close()
        return jsonify({'message': 'Resolution proposed. Exception submitted for Manager Approval.', 'status': 'Pending Approval'})

    # Direct Status Update
    approval_st = exc_dict['approval_status']
    closed_by = exc_dict['closed_by']
    closed_at = exc_dict['closed_at']
    
    if new_status == 'Closed':
        closed_by = g.current_user['id']
        closed_at = 'CURRENT_TIMESTAMP'
        approval_st = 'Approved'

    cursor.execute("""
        UPDATE exceptions 
        SET status = ?, root_cause = ?, resolution_summary = ?, approval_status = ?
        WHERE id = ?
    """, (new_status, root_cause or exc_dict['root_cause'], resolution_summary or exc_dict['resolution_summary'], approval_st, exc_id))
    
    conn.commit()
    conn.close()
    
    log_audit_event(action='UPDATE_EXCEPTION_STATUS', entity='exceptions', record_id=str(exc_id), previous_value={'status': exc_dict['status']}, new_value={'status': new_status})
    return jsonify({'message': f'Exception status updated to {new_status}'})

@exception_bp.route('/<int:exc_id>/comments', methods=['POST'])
@require_auth
def add_exception_comment(exc_id):
    data = request.json or {}
    comment = data.get('comment')
    
    if not comment:
        return jsonify({'error': 'Comment text is required.'}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO exception_comments (exception_id, user_id, comment)
        VALUES (?, ?, ?)
    """, (exc_id, g.current_user['id'], comment))
    
    conn.commit()
    conn.close()
    return jsonify({'message': 'Comment added successfully'})
