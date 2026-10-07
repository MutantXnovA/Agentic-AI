from flask import Blueprint, request, jsonify, g
from auth import verify_password, hash_password, generate_jwt, require_auth
from database import get_db
from audit import log_audit_event

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required.'}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? OR email = ?", (username, username))
    user = cursor.fetchone()
    conn.close()
    
    if not user or not user['is_active']:
        return jsonify({'error': 'Invalid credentials or inactive account.'}), 401
        
    if not verify_password(password, user['password_hash'], user['salt']):
        return jsonify({'error': 'Invalid username or password.'}), 401
        
    user_dict = dict(user)
    token = generate_jwt(user_dict)
    
    log_audit_event(
        action='USER_LOGIN',
        entity='users',
        record_id=str(user['id']),
        new_value={'username': user['username'], 'role': user['role']},
        user_override=user_dict
    )
    
    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'full_name': user['full_name'],
            'role': user['role'],
            'department': user['department']
        }
    })

@auth_bp.route('/demo-login', methods=['POST'])
def demo_login():
    """Auto-login as admin for demo/development mode. Issues a real JWT."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    user = cursor.fetchone()
    conn.close()

    if not user:
        return jsonify({'error': 'Admin user not found. Database may not be seeded.'}), 500

    user_dict = dict(user)
    token = generate_jwt(user_dict)

    return jsonify({
        'message': 'Demo login successful',
        'token': token,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'full_name': user['full_name'],
            'role': user['role'],
            'department': user['department']
        }
    })

@auth_bp.route('/me', methods=['GET'])
@require_auth
def get_current_user():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, full_name, role, department, created_at FROM users WHERE id = ?", (g.current_user['id'],))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    return jsonify({'user': dict(user)})

@auth_bp.route('/password', methods=['PUT'])
@require_auth
def change_password():
    data = request.json or {}
    old_pwd = data.get('old_password')
    new_pwd = data.get('new_password')
    
    if not old_pwd or not new_pwd:
        return jsonify({'error': 'Both old and new passwords are required.'}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (g.current_user['id'],))
    user = cursor.fetchone()
    
    if not verify_password(old_pwd, user['password_hash'], user['salt']):
        conn.close()
        return jsonify({'error': 'Current password is incorrect.'}), 400
        
    new_hash, new_salt = hash_password(new_pwd)
    cursor.execute("UPDATE users SET password_hash = ?, salt = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_hash, new_salt, user['id']))
    conn.commit()
    conn.close()
    
    log_audit_event(action='CHANGE_PASSWORD', entity='users', record_id=str(user['id']))
    return jsonify({'message': 'Password updated successfully.'})
