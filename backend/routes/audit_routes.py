from flask import Blueprint, request, jsonify
from auth import require_auth, require_role
from database import get_db
from config import Config

audit_bp = Blueprint('audit', __name__, url_prefix='/api/audit')

@audit_bp.route('', methods=['GET'])
@require_auth
@require_role([Config.ROLE_SUPER_ADMIN, Config.ROLE_FINANCE_ADMIN, Config.ROLE_FINANCE_MANAGER, Config.ROLE_REVIEWER, Config.ROLE_AUDITOR])
def get_audit_logs():
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 30))
    offset = (page - 1) * limit
    entity = request.args.get('entity')
    action = request.args.get('action')
    search = request.args.get('search', '').strip()
    
    conn = get_db()
    cursor = conn.cursor()
    
    where = ["1=1"]
    params = []
    
    if entity:
        where.append("entity = ?")
        params.append(entity)
    if action:
        where.append("action = ?")
        params.append(action)
    if search:
        where.append("(username LIKE ? OR action LIKE ? OR entity LIKE ? OR record_id LIKE ?)")
        s_pat = f"%{search}%"
        params.extend([s_pat] * 4)

    where_sql = " AND ".join(where)

    cursor.execute(f"SELECT COUNT(*) as total FROM audit_logs WHERE {where_sql}", params)
    total_records = cursor.fetchone()['total']

    query = f"""
        SELECT * FROM audit_logs 
        WHERE {where_sql} 
        ORDER BY id DESC 
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    cursor.execute(query, params)
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({
        'logs': logs,
        'pagination': {
            'total': total_records,
            'page': page,
            'limit': limit,
            'total_pages': (total_records + limit - 1) // limit
        }
    })
