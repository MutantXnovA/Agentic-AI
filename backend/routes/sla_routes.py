from flask import Blueprint, request, jsonify
from auth import require_auth, require_role
from database import get_db
from config import Config

sla_bp = Blueprint('sla', __name__, url_prefix='/api/sla')

@sla_bp.route('/rules', methods=['GET'])
@require_auth
def get_sla_rules():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sla_rules ORDER BY allowed_hours ASC")
    rules = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'sla_rules': rules})

@sla_bp.route('/metrics', methods=['GET'])
@require_auth
def get_sla_metrics():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            COUNT(CASE WHEN sla_status = 'Within SLA' THEN 1 END) as within_sla,
            COUNT(CASE WHEN sla_status = 'At Risk' THEN 1 END) as at_risk,
            COUNT(CASE WHEN sla_status = 'SLA Breached' THEN 1 END) as breached,
            COUNT(*) as total_active
        FROM exceptions
        WHERE status NOT IN ('Closed', 'Resolved')
    """)
    metrics = cursor.fetchone()
    conn.close()
    return jsonify({'metrics': dict(metrics)})
