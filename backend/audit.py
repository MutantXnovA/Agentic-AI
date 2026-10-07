import json
from flask import request, g, has_request_context
from database import get_db

def log_audit_event(action: str, entity: str, record_id: str = None, previous_value = None, new_value = None, reason: str = None, user_override: dict = None):
    """
    Writes an immutable record to audit_logs table.
    Captures user details, action, entity, JSON diffs, IP address, and timestamp.
    Safely handles execution inside or outside Flask HTTP request contexts.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    user_id = None
    username = 'System'
    ip_address = '127.0.0.1'
    
    if user_override:
        user_id = user_override.get('id')
        username = user_override.get('username', 'System')
    elif has_request_context():
        if hasattr(g, 'current_user') and g.current_user:
            user_id = g.current_user.get('id')
            username = g.current_user.get('username', 'System')
        ip_address = request.remote_addr or '127.0.0.1'
        
    prev_json = json.dumps(previous_value, default=str) if previous_value is not None else None
    new_json = json.dumps(new_value, default=str) if new_value is not None else None
    
    cursor.execute('''
        INSERT INTO audit_logs (user_id, username, action, entity, record_id, previous_value_json, new_value_json, ip_address, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, action, entity, str(record_id) if record_id else None, prev_json, new_json, ip_address, reason))
    
    conn.commit()
    conn.close()
