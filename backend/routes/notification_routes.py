from flask import Blueprint, jsonify, g
from auth import require_auth
from database import get_db

notif_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')

@notif_bp.route('', methods=['GET'])
@require_auth
def get_user_notifications():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM notifications 
        WHERE user_id = ? 
        ORDER BY id DESC LIMIT 20
    """, (g.current_user['id'],))
    notifications = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("SELECT COUNT(*) as unread FROM notifications WHERE user_id = ? AND is_read = 0", (g.current_user['id'],))
    unread_cnt = cursor.fetchone()['unread']
    
    conn.close()
    return jsonify({
        'notifications': notifications,
        'unread_count': unread_cnt
    })

@notif_bp.route('/read-all', methods=['PUT'])
@require_auth
def mark_all_read():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (g.current_user['id'],))
    conn.commit()
    conn.close()
    return jsonify({'message': 'All notifications marked as read'})
