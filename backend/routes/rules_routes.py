import json
from flask import Blueprint, request, jsonify, g
from auth import require_auth, require_role
from database import get_db
from audit import log_audit_event
from config import Config

rules_bp = Blueprint('rules', __name__, url_prefix='/api/rules')

@rules_bp.route('', methods=['GET'])
@require_auth
def list_rules():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reconciliation_rules ORDER BY priority ASC")
    rules = []
    for row in cursor.fetchall():
        r = dict(row)
        if isinstance(r['match_fields'], str):
            try:
                r['match_fields'] = json.loads(r['match_fields'])
            except Exception:
                pass
        rules.append(r)
    conn.close()
    return jsonify({'rules': rules})

@rules_bp.route('', methods=['POST'])
@require_auth
@require_role([Config.ROLE_SUPER_ADMIN, Config.ROLE_FINANCE_ADMIN])
def create_rule():
    data = request.json or {}
    rule_name = data.get('rule_name')
    priority = data.get('priority')
    match_fields = data.get('match_fields', [])
    date_tol = data.get('date_tolerance_days', 0)
    amount_tol = data.get('amount_tolerance', 0.0)
    currency_tol = data.get('currency_tolerance', 1)
    fuzzy_thresh = data.get('fuzzy_threshold', 85)
    description = data.get('description', '')
    
    if not rule_name or not priority or not match_fields:
        return jsonify({'error': 'Rule name, priority, and match fields are required.'}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    
    fields_json = json.dumps(match_fields) if isinstance(match_fields, list) else match_fields
    
    try:
        cursor.execute("""
            INSERT INTO reconciliation_rules (rule_name, priority, match_fields, date_tolerance_days, amount_tolerance, currency_tolerance, fuzzy_threshold, description, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (rule_name, priority, fields_json, date_tol, amount_tol, currency_tol, fuzzy_thresh, description, g.current_user['id']))
        rule_id = cursor.lastrowid
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({'error': f'Failed to create rule: {str(e)}'}), 400

    conn.close()
    log_audit_event(action='CREATE_RECONCILIATION_RULE', entity='reconciliation_rules', record_id=str(rule_id), new_value={'rule_name': rule_name, 'priority': priority})
    return jsonify({'message': 'Rule created successfully', 'id': rule_id}), 201

@rules_bp.route('/<int:rule_id>', methods=['PUT'])
@require_auth
@require_role([Config.ROLE_SUPER_ADMIN, Config.ROLE_FINANCE_ADMIN])
def update_rule(rule_id):
    data = request.json or {}
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM reconciliation_rules WHERE id = ?", (rule_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        return jsonify({'error': 'Rule not found'}), 404
        
    rule_name = data.get('rule_name', existing['rule_name'])
    priority = data.get('priority', existing['priority'])
    match_fields = data.get('match_fields', existing['match_fields'])
    fields_json = json.dumps(match_fields) if isinstance(match_fields, list) else match_fields
    date_tol = data.get('date_tolerance_days', existing['date_tolerance_days'])
    amount_tol = data.get('amount_tolerance', existing['amount_tolerance'])
    fuzzy_thresh = data.get('fuzzy_threshold', existing['fuzzy_threshold'])
    is_active = data.get('is_active', existing['is_active'])
    
    cursor.execute("""
        UPDATE reconciliation_rules
        SET rule_name = ?, priority = ?, match_fields = ?, date_tolerance_days = ?, amount_tolerance = ?, fuzzy_threshold = ?, is_active = ?
        WHERE id = ?
    """, (rule_name, priority, fields_json, date_tol, amount_tol, fuzzy_thresh, is_active, rule_id))
    
    conn.commit()
    conn.close()
    
    log_audit_event(action='UPDATE_RECONCILIATION_RULE', entity='reconciliation_rules', record_id=str(rule_id), previous_value=dict(existing), new_value={'rule_name': rule_name, 'is_active': is_active})
    return jsonify({'message': 'Rule updated successfully'})
