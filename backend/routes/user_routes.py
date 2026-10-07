from flask import Blueprint, request, jsonify, g
from auth import require_auth, require_role, hash_password
from database import get_db
from audit import log_audit_event
from config import Config

user_bp = Blueprint('users', __name__, url_prefix='/api/users')

@user_bp.route('', methods=['GET'])
@require_auth
def list_users():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, email, full_name, role, department, is_active, created_at 
        FROM users 
        ORDER BY id ASC
    """)
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'users': users, 'roles': Config.ROLES_LIST})

@user_bp.route('', methods=['POST'])
@require_auth
@require_role([Config.ROLE_SUPER_ADMIN, Config.ROLE_FINANCE_ADMIN])
def create_user():
    data = request.json or {}
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    full_name = data.get('full_name')
    role = data.get('role', Config.ROLE_RECON_ANALYST)
    department = data.get('department', 'Finance')
    
    if not username or not email or not password or not full_name:
        return jsonify({'error': 'Username, email, password, and full name are required.'}), 400
        
    phash, salt = hash_password(password)
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, salt, full_name, role, department)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (username, email, phash, salt, full_name, role, department))
        new_id = cursor.lastrowid
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({'error': f'Failed to create user: {str(e)}'}), 400
        
    conn.close()
    log_audit_event(action='CREATE_USER', entity='users', record_id=str(new_id), new_value={'username': username, 'role': role})
    return jsonify({'message': 'User created successfully', 'id': new_id}), 201

@user_bp.route('/<int:user_id>', methods=['PUT'])
@require_auth
@require_role([Config.ROLE_SUPER_ADMIN, Config.ROLE_FINANCE_ADMIN])
def update_user(user_id):
    data = request.json or {}
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
        
    role = data.get('role', existing['role'])
    full_name = data.get('full_name', existing['full_name'])
    department = data.get('department', existing['department'])
    is_active = data.get('is_active', existing['is_active'])
    
    cursor.execute("""
        UPDATE users SET role = ?, full_name = ?, department = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (role, full_name, department, is_active, user_id))
    
    conn.commit()
    conn.close()
    
    log_audit_event(
        action='UPDATE_USER', 
        entity='users', 
        record_id=str(user_id), 
        previous_value=dict(existing), 
        new_value={'role': role, 'full_name': full_name, 'is_active': is_active}
    )
    
    return jsonify({'message': 'User updated successfully'})
