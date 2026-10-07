import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from config import Config
from database import init_db
from seed_data import seed_database

# Import Route Blueprints
from routes.auth_routes import auth_bp
from routes.user_routes import user_bp
from routes.transaction_routes import txn_bp
from routes.ingestion_routes import ingestion_bp
from routes.reconciliation_routes import recon_bp
from routes.rules_routes import rules_bp
from routes.exception_routes import exception_bp
from routes.sla_routes import sla_bp
from routes.report_routes import report_bp
from routes.audit_routes import audit_bp
from routes.notification_routes import notif_bp

def create_app():
    # Set static folder to frontend directory
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
    app = Flask(__name__, static_folder=frontend_dir, static_url_path='')
    
    app.config.from_object(Config)
    CORS(app)
    
    # Initialize DB & Seed Data
    init_db()
    seed_database()
    
    # Register API Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(txn_bp)
    app.register_blueprint(ingestion_bp)
    app.register_blueprint(recon_bp)
    app.register_blueprint(rules_bp)
    app.register_blueprint(exception_bp)
    app.register_blueprint(sla_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(notif_bp)
    
    # Serve SPA Frontend
    @app.route('/')
    def serve_frontend():
        return send_from_directory(app.static_folder, 'index.html')

    @app.route('/<path:path>')
    def serve_static(path):
        file_path = os.path.join(app.static_folder, path)
        if os.path.exists(file_path):
            return send_from_directory(app.static_folder, path)
        # Fallback to index.html for client-side routing
        return send_from_directory(app.static_folder, 'index.html')

    # Global Error Handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Resource not found'}), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

    return app

app = create_app()

if __name__ == '__main__':
    print("Starting ReconX Financial Reconciliation Server on http://127.0.0.1:5000 ...")
    app.run(host='127.0.0.1', port=5000, debug=True, use_reloader=False)
