import hashlib
import secrets
import jwt
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, jsonify, g
from config import Config
from database import get_db

import firebase_admin
from firebase_admin import credentials, auth as firebase_auth

# Initialize Firebase Admin App
try:
    firebase_admin.get_app()
except ValueError:
    import os
    # Assuming auth.py is in backend folder where serviceAccountKey.json is
    key_path = os.path.join(os.path.dirname(__file__), 'serviceAccountKey.json')
    cred = credentials.Certificate(key_path)
    firebase_admin.initialize_app(cred)

def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """Generates a salted SHA-256 hash for password storage."""
    if not salt:
        salt = secrets.token_hex(16)
    salted_pwd = (password + salt).encode('utf-8')
    pwd_hash = hashlib.sha256(salted_pwd).hexdigest()
    return pwd_hash, salt

def verify_password(password: str, pwd_hash: str, salt: str) -> bool:
    """Verifies a plain password against the stored hash and salt."""
    test_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(test_hash, pwd_hash)

def generate_jwt(user_data: dict) -> str:
    """Generates a signed JWT token valid for Config.JWT_EXPIRATION_HOURS."""
    payload = {
        'id': user_data['id'],
        'username': user_data['username'],
        'email': user_data['email'],
        'role': user_data['role'],
        'full_name': user_data['full_name'],
        'exp': datetime.now(timezone.utc) + timedelta(hours=Config.JWT_EXPIRATION_HOURS),
        'iat': datetime.now(timezone.utc)
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm=Config.JWT_ALGORITHM)

def decode_jwt(token: str) -> dict:
    """Decodes and validates a JWT token."""
    try:
        return jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def require_auth(f):
    """Flask decorator ensuring request has a valid Bearer JWT token from Firebase."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        token = None
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            token = request.args.get('token')
            
        if not token:
            return jsonify({'error': 'Authentication required. Missing Bearer token.'}), 401
            
        try:
            # Verify Firebase ID token
            decoded_token = firebase_auth.verify_id_token(token)
            email = decoded_token.get('email')
            uid = decoded_token.get('uid')
            
            # Look up user in local database
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            
            if not user:
                # Auto-create user if they registered via Firebase
                username = email.split('@')[0]
                full_name = username.capitalize()
                cursor.execute("""
                    INSERT INTO users (username, email, password_hash, salt, full_name, role, department, is_active)
                    VALUES (?, ?, 'firebase_auth', 'firebase_auth', ?, 'super_admin', 'Finance Operations', 1)
                """, (username, email, full_name))
                conn.commit()
                user_id = cursor.lastrowid
                
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                user = cursor.fetchone()
                
            conn.close()
            g.current_user = dict(user)
            
        except Exception as e:
            return jsonify({'error': f'Invalid or expired token. Please log in again. Details: {str(e)}'}), 401
            
        return f(*args, **kwargs)
    return decorated_function

def require_role(allowed_roles: list):
    """Flask decorator restricting route execution to specified roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'current_user') or not g.current_user:
                return jsonify({'error': 'Authentication required'}), 401
            
            user_role = g.current_user.get('role')
            if user_role not in allowed_roles and user_role != Config.ROLE_SUPER_ADMIN:
                return jsonify({
                    'error': f'Permission denied. Role "{user_role}" does not have access to this resource.'
                }), 403
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator
