import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'reconx-enterprise-super-secret-key-2026-financial-reconciliation')
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRATION_HOURS = 24
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, 'reconx_financial.db')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    
    # System Roles
    ROLE_SUPER_ADMIN = 'super_admin'
    ROLE_FINANCE_ADMIN = 'finance_admin'
    ROLE_FINANCE_MANAGER = 'finance_manager'
    ROLE_RECON_ANALYST = 'reconciliation_analyst'
    ROLE_REVIEWER = 'reviewer'
    ROLE_AUDITOR = 'auditor'
    ROLE_READONLY = 'readonly'
    
    ROLES_LIST = [
        ROLE_SUPER_ADMIN,
        ROLE_FINANCE_ADMIN,
        ROLE_FINANCE_MANAGER,
        ROLE_RECON_ANALYST,
        ROLE_REVIEWER,
        ROLE_AUDITOR,
        ROLE_READONLY
    ]
    
    # SLA Defaults (Hours)
    SLA_DEFAULTS = {
        'Critical': 4,
        'High': 24,
        'Medium': 72,  # 3 days
        'Low': 168     # 7 days
    }

os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
