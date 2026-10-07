import sqlite3
import json
from datetime import datetime
from config import Config

def get_db():
    conn = sqlite3.connect(Config.DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    # Enable foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON;")
    # WAL mode for better concurrency (prevents "database is locked" errors)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            department TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. Roles Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT
        )
    ''')
    
    # 3. Permissions Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            resource TEXT NOT NULL,
            action TEXT NOT NULL,
            UNIQUE(role, resource, action)
        )
    ''')
    
    # 4. Entities Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            country TEXT,
            currency TEXT DEFAULT 'USD'
        )
    ''')
    
    # 5. Accounts Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id INTEGER NOT NULL,
            account_number TEXT UNIQUE NOT NULL,
            account_name TEXT NOT NULL,
            bank_name TEXT,
            currency TEXT NOT NULL,
            FOREIGN KEY (entity_id) REFERENCES entities(id)
        )
    ''')
    
    # 6. Transaction Sources Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transaction_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            description TEXT
        )
    ''')
    
    # 7. Import Batches Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS import_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_code TEXT UNIQUE NOT NULL,
            source_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            total_records INTEGER DEFAULT 0,
            accepted_records INTEGER DEFAULT 0,
            rejected_records INTEGER DEFAULT 0,
            duplicate_records INTEGER DEFAULT 0,
            errors_json TEXT,
            uploaded_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES transaction_sources(id),
            FOREIGN KEY (uploaded_by) REFERENCES users(id)
        )
    ''')
    
    # 8. Transactions Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER,
            external_txn_id TEXT NOT NULL,
            ref_number TEXT,
            txn_date TEXT NOT NULL,
            value_date TEXT,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            debit_credit TEXT NOT NULL,
            account_id INTEGER,
            entity_id INTEGER,
            description TEXT,
            counterparty TEXT,
            source_id INTEGER NOT NULL,
            payment_method TEXT,
            status TEXT DEFAULT 'Pending',
            is_matched INTEGER DEFAULT 0,
            raw_data_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (batch_id) REFERENCES import_batches(id),
            FOREIGN KEY (account_id) REFERENCES accounts(id),
            FOREIGN KEY (entity_id) REFERENCES entities(id),
            FOREIGN KEY (source_id) REFERENCES transaction_sources(id)
        )
    ''')
    
    # 9. Reconciliation Rules Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reconciliation_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_name TEXT NOT NULL,
            priority INTEGER NOT NULL UNIQUE,
            match_fields TEXT NOT NULL, -- JSON array e.g. ["ref_number", "amount", "currency"]
            date_tolerance_days INTEGER DEFAULT 0,
            amount_tolerance REAL DEFAULT 0.0,
            currency_tolerance INTEGER DEFAULT 1,
            fuzzy_threshold INTEGER DEFAULT 85,
            is_active INTEGER DEFAULT 1,
            description TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    ''')
    
    # 10. Reconciliation Runs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reconciliation_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_code TEXT UNIQUE NOT NULL,
            initiated_by INTEGER NOT NULL,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            total_processed INTEGER DEFAULT 0,
            matched_count INTEGER DEFAULT 0,
            unmatched_count INTEGER DEFAULT 0,
            partial_count INTEGER DEFAULT 0,
            exceptions_created INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Processing',
            FOREIGN KEY (initiated_by) REFERENCES users(id)
        )
    ''')
    
    # 11. Reconciliation Results Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reconciliation_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            source_a_id INTEGER NOT NULL,
            source_b_id INTEGER,
            match_status TEXT NOT NULL, -- Matched, Unmatched, Partial Match, Amount Mismatch, Date Mismatch, Manual Match
            matched_rule_id INTEGER,
            match_score REAL DEFAULT 0.0,
            amount_diff REAL DEFAULT 0.0,
            date_diff_days INTEGER DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (run_id) REFERENCES reconciliation_runs(id),
            FOREIGN KEY (source_a_id) REFERENCES transactions(id),
            FOREIGN KEY (source_b_id) REFERENCES transactions(id),
            FOREIGN KEY (matched_rule_id) REFERENCES reconciliation_rules(id)
        )
    ''')
    
    # 12. Exceptions Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exceptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exception_code TEXT UNIQUE NOT NULL,
            transaction_id INTEGER NOT NULL,
            recon_result_id INTEGER,
            exception_type TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            priority TEXT NOT NULL, -- Critical, High, Medium, Low
            severity TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'New', -- New, Open, Investigating, Pending Information, Pending Approval, Resolved, Rejected, Closed, Reopened
            owner_id INTEGER,
            department TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            due_date TIMESTAMP NOT NULL,
            sla_status TEXT DEFAULT 'Within SLA', -- Within SLA, At Risk, SLA Breached
            ageing_days INTEGER DEFAULT 0,
            root_cause TEXT,
            resolution_summary TEXT,
            approval_status TEXT DEFAULT 'Not Required', -- Not Required, Pending Approval, Approved, Rejected
            closed_at TIMESTAMP,
            closed_by INTEGER,
            FOREIGN KEY (transaction_id) REFERENCES transactions(id),
            FOREIGN KEY (recon_result_id) REFERENCES reconciliation_results(id),
            FOREIGN KEY (owner_id) REFERENCES users(id),
            FOREIGN KEY (closed_by) REFERENCES users(id)
        )
    ''')
    
    # 13. Exception Comments Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exception_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exception_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            comment TEXT NOT NULL,
            attachments_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (exception_id) REFERENCES exceptions(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # 14. Exception Attachments Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exception_attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exception_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            uploaded_by INTEGER NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (exception_id) REFERENCES exceptions(id),
            FOREIGN KEY (uploaded_by) REFERENCES users(id)
        )
    ''')
    
    # 15. Exception Assignments Log Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exception_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exception_id INTEGER NOT NULL,
            previous_owner_id INTEGER,
            new_owner_id INTEGER NOT NULL,
            assigned_by INTEGER NOT NULL,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (exception_id) REFERENCES exceptions(id),
            FOREIGN KEY (previous_owner_id) REFERENCES users(id),
            FOREIGN KEY (new_owner_id) REFERENCES users(id),
            FOREIGN KEY (assigned_by) REFERENCES users(id)
        )
    ''')
    
    # 16. Approvals Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exception_id INTEGER NOT NULL,
            requested_by INTEGER NOT NULL,
            approved_by INTEGER,
            proposed_resolution TEXT NOT NULL,
            status TEXT DEFAULT 'Pending Approval', -- Pending Approval, Approved, Rejected
            comments TEXT,
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            acted_at TIMESTAMP,
            FOREIGN KEY (exception_id) REFERENCES exceptions(id),
            FOREIGN KEY (requested_by) REFERENCES users(id),
            FOREIGN KEY (approved_by) REFERENCES users(id)
        )
    ''')
    
    # 17. SLA Rules Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sla_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            priority TEXT UNIQUE NOT NULL,
            allowed_hours INTEGER NOT NULL,
            warning_hours INTEGER NOT NULL,
            escalation_email TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # 18. Audit Logs Table (Immutable Log)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            action TEXT NOT NULL,
            entity TEXT NOT NULL,
            record_id TEXT,
            previous_value_json TEXT,
            new_value_json TEXT,
            ip_address TEXT,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 19. Notifications Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT DEFAULT 'info',
            is_read INTEGER DEFAULT 0,
            link TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Indexes for High Performance Querying
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_txn_date ON transactions(txn_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_txn_ext_id ON transactions(external_txn_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_txn_ref ON transactions(ref_number);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_txn_source ON transactions(source_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_txn_matched ON transactions(is_matched);")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recon_status ON reconciliation_results(match_status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_exc_status ON exceptions(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_exc_priority ON exceptions(priority);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_exc_owner ON exceptions(owner_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_exc_due_date ON exceptions(due_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs(entity);")
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database schema initialized successfully.")
