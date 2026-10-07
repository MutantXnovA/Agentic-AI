import random
from datetime import datetime, timedelta
from database import get_db, init_db
from auth import hash_password

def seed_database():
    init_db()
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if already seeded
    cursor.execute("SELECT COUNT(*) as count FROM users")
    if cursor.fetchone()['count'] > 0:
        print("Database already contains seed data. Skipping seed.")
        conn.close()
        return

    print("Seeding database with enterprise financial reconciliation dataset...")

    # 1. Seed Users (All 7 Roles)
    users = [
        ('admin', 'admin@reconx.fintech', 'Admin@123', 'Alexander Wright', 'super_admin', 'Executive Office'),
        ('finadmin', 'finadmin@reconx.fintech', 'Admin@123', 'Victoria Sterling', 'finance_admin', 'Finance Ops'),
        ('manager', 'manager@reconx.fintech', 'Manager@123', 'Marcus Vance', 'finance_manager', 'Reconciliation'),
        ('analyst1', 'analyst1@reconx.fintech', 'Analyst@123', 'Elena Rostova', 'reconciliation_analyst', 'Reconciliation'),
        ('analyst2', 'analyst2@reconx.fintech', 'Analyst@123', 'David Chen', 'reconciliation_analyst', 'Reconciliation'),
        ('reviewer', 'reviewer@reconx.fintech', 'Reviewer@123', 'Sophia Martinez', 'reviewer', 'Internal Audit & Review'),
        ('auditor', 'auditor@reconx.fintech', 'Auditor@123', 'Jonathan Blake', 'auditor', 'Risk & Compliance'),
        ('viewer', 'viewer@reconx.fintech', 'Viewer@123', 'Rachel Amber', 'readonly', 'Executive Viewer')
    ]
    
    user_ids = {}
    for uname, email, pwd, fname, role, dept in users:
        phash, salt = hash_password(pwd)
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, salt, full_name, role, department)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (uname, email, phash, salt, fname, role, dept))
        user_ids[uname] = cursor.lastrowid

    # 2. Seed Entities & Accounts
    cursor.execute("INSERT INTO entities (code, name, country, currency) VALUES ('ENT-US', 'Acme Global Corp US', 'USA', 'USD')")
    ent_us_id = cursor.lastrowid
    cursor.execute("INSERT INTO entities (code, name, country, currency) VALUES ('ENT-IN', 'Acme FinTech India Pvt Ltd', 'India', 'INR')")
    ent_in_id = cursor.lastrowid

    accounts = [
        (ent_us_id, 'ACC-CHASE-9941', 'Chase Merchant Primary USD', 'JPMorgan Chase', 'USD'),
        (ent_us_id, 'ACC-STRIPE-8812', 'Stripe Gateway Operating USD', 'Stripe Payments', 'USD'),
        (ent_in_id, 'ACC-HDFC-4410', 'HDFC Merchant Escrow INR', 'HDFC Bank Ltd', 'INR'),
        (ent_in_id, 'ACC-RAZOR-2201', 'Razorpay Collections INR', 'Razorpay Software', 'INR')
    ]
    acc_ids = []
    for ent_id, acc_num, acc_name, bank, curr in accounts:
        cursor.execute("INSERT INTO accounts (entity_id, account_number, account_name, bank_name, currency) VALUES (?, ?, ?, ?, ?)",
                       (ent_id, acc_num, acc_name, bank, curr))
        acc_ids.append(cursor.lastrowid)

    # 3. Seed Transaction Sources
    sources = [
        ('SRC-BANK-STMT', 'Bank Statement Feed', 'Bank', 'Direct SFTP electronic statement feed'),
        ('SRC-INTERNAL-LEDGER', 'ERP General Ledger', 'Ledger', 'NetSuite / SAP Core Financial Ledger'),
        ('SRC-STRIPE-PG', 'Stripe Payment Gateway', 'Gateway', 'Stripe API Settlement Feed'),
        ('SRC-RAZORPAY-PG', 'Razorpay Payment Gateway', 'Gateway', 'Razorpay Webhook Clearing Feed')
    ]
    src_ids = {}
    for code, sname, stype, desc in sources:
        cursor.execute("INSERT INTO transaction_sources (code, name, type, description) VALUES (?, ?, ?, ?)", (code, sname, stype, desc))
        src_ids[code] = cursor.lastrowid

    # 4. Seed SLA Rules
    cursor.execute("INSERT INTO sla_rules (priority, allowed_hours, warning_hours, escalation_email) VALUES ('Critical', 4, 2, 'escalations-critical@reconx.fintech')")
    cursor.execute("INSERT INTO sla_rules (priority, allowed_hours, warning_hours, escalation_email) VALUES ('High', 24, 18, 'escalations-high@reconx.fintech')")
    cursor.execute("INSERT INTO sla_rules (priority, allowed_hours, warning_hours, escalation_email) VALUES ('Medium', 72, 48, 'ops-managers@reconx.fintech')")
    cursor.execute("INSERT INTO sla_rules (priority, allowed_hours, warning_hours, escalation_email) VALUES ('Low', 168, 120, 'ops-team@reconx.fintech')")

    # 5. Seed Reconciliation Rules (Configurable Rules 1-4)
    rules = [
        ("Rule 1: Exact Match (ID + Amount + Currency)", 1, '["external_txn_id", "amount", "currency"]', 0, 0.0, 1, 100, "Requires identical transaction ID, exact amount, and currency."),
        ("Rule 2: Reference + Amount + Date ±1 Day", 2, '["ref_number", "amount", "txn_date"]', 1, 0.0, 1, 90, "Matches normalized reference number with exact amount within 1 day date tolerance."),
        ("Rule 3: Amount + Counterparty + Date ±2 Days", 3, '["amount", "counterparty", "txn_date"]', 2, 0.5, 1, 85, "Matches transaction amount within $0.50 tolerance and fuzzy counterparty name within 2 days."),
        ("Rule 4: Reference + Date ±3 Days Tolerance", 4, '["ref_number", "txn_date"]', 3, 5.0, 1, 80, "Matches reference number within 3 days date tolerance and up to $5 amount mismatch.")
    ]
    for rname, prio, mfields, dtol, atol, ctol, fthresh, desc in rules:
        cursor.execute("""
            INSERT INTO reconciliation_rules (rule_name, priority, match_fields, date_tolerance_days, amount_tolerance, currency_tolerance, fuzzy_threshold, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (rname, prio, mfields, dtol, atol, ctol, fthresh, user_ids['admin']))

    # 6. Seed Import Batch
    cursor.execute("""
        INSERT INTO import_batches (batch_code, source_id, filename, total_records, accepted_records, rejected_records, duplicate_records, uploaded_by)
        VALUES ('BATCH-20261001-01', ?, 'bank_feed_oct2026.csv', 120, 118, 2, 0, ?)
    """, (src_ids['SRC-BANK-STMT'], user_ids['analyst1']))
    batch_id = cursor.lastrowid

    # 7. Generate 120 Realistic Transactions (Source A: Bank Statement & Source B: Internal Ledger)
    counterparties = ['Stripe Payments Inc', 'Apex Global Software', 'Cloudflare CDN', 'AWS Hosting Services', 'Razorpay Merchant', 'Nexus Logistics', 'Veritas Advisory', 'Delta Telecom']
    currencies = ['USD', 'USD', 'INR', 'EUR']
    
    txns_a = []
    txns_b = []
    
    base_date = datetime(2026, 9, 25)
    
    for i in range(1, 61):
        txn_date = (base_date + timedelta(days=i % 10, hours=i % 12)).strftime('%Y-%m-%d %H:%M:%S')
        ref_num = f"PAY-{10000 + i}"
        ext_id_a = f"BNK-{80000 + i}"
        ext_id_b = f"BNK-{80000 + i}" if i <= 40 else f"LDG-{90000 + i}"
        
        amount = round(random.uniform(150.0, 18500.0), 2)
        curr = currencies[i % len(currencies)]
        cp = counterparties[i % len(counterparties)]
        
        # Introduce specific reconciliation test scenarios:
        # Scenario 1 (1..35): Perfect Exact Match
        # Scenario 2 (36..42): Amount Mismatch (Bank has $10,000, Ledger has $9,850 due to fee)
        # Scenario 3 (43..48): Date Mismatch (1 day difference)
        # Scenario 4 (49..54): Missing in Source B (Unmatched Bank transaction)
        # Scenario 5 (55..60): Missing in Source A (Unmatched Ledger transaction)
        
        amt_a = amount
        amt_b = amount
        date_b = txn_date
        
        if 36 <= i <= 42:
            amt_b = round(amount - random.choice([15.0, 50.0, 150.0]), 2) # Fee difference
        elif 43 <= i <= 48:
            date_b = (base_date + timedelta(days=(i % 10) + 1, hours=i % 12)).strftime('%Y-%m-%d %H:%M:%S')
            
        # Insert Source A (Bank)
        if i <= 54:
            cursor.execute("""
                INSERT INTO transactions (batch_id, external_txn_id, ref_number, txn_date, amount, currency, debit_credit, account_id, entity_id, description, counterparty, source_id, payment_method, status, is_matched)
                VALUES (?, ?, ?, ?, ?, ?, 'Credit', ?, ?, ?, ?, ?, 'Wire/ACH', 'Pending', 0)
            """, (batch_id, ext_id_a, ref_num, txn_date, amt_a, curr, acc_ids[0], ent_us_id, f"Settlement payment from {cp}", cp, src_ids['SRC-BANK-STMT']))
            txn_a_db_id = cursor.lastrowid
            txns_a.append({'id': txn_a_db_id, 'ext_id': ext_id_a, 'ref': ref_num, 'amount': amt_a, 'date': txn_date, 'curr': curr, 'index': i})

        # Insert Source B (Ledger)
        if i <= 48 or i >= 55:
            cursor.execute("""
                INSERT INTO transactions (batch_id, external_txn_id, ref_number, txn_date, amount, currency, debit_credit, account_id, entity_id, description, counterparty, source_id, payment_method, status, is_matched)
                VALUES (?, ?, ?, ?, ?, ?, 'Debit', ?, ?, ?, ?, ?, 'ERP Posting', 'Pending', 0)
            """, (batch_id, ext_id_b, ref_num, date_b, amt_b, curr, acc_ids[1], ent_us_id, f"Invoice posting for {cp}", cp, src_ids['SRC-INTERNAL-LEDGER']))
            txn_b_db_id = cursor.lastrowid
            txns_b.append({'id': txn_b_db_id, 'ext_id': ext_id_b, 'ref': ref_num, 'amount': amt_b, 'date': date_b, 'curr': curr, 'index': i})

    conn.commit()

    # 8. Run Initial Reconciliation to populate Reconciliation Results & Exceptions automatically
    from reconciliation_engine import run_reconciliation
    recon_summary = run_reconciliation(user_id=user_ids['admin'])
    print(f"Reconciliation Run completed: Matched={recon_summary['matched_count']}, Partial/Mismatched={recon_summary['partial_count']}, Unmatched={recon_summary['unmatched_count']}, Exceptions Created={recon_summary['exceptions_created']}")

    # 9. Update sample exception statuses & add realistic investigation notes, comments, and approvals
    cursor.execute("SELECT id, exception_code, priority, amount, currency, exception_type FROM exceptions")
    exc_list = cursor.fetchall()
    
    statuses_cycle = ['New', 'Investigating', 'Pending Approval', 'Resolved', 'Closed']
    
    for idx, exc in enumerate(exc_list):
        status = statuses_cycle[idx % len(statuses_cycle)]
        assigned_owner = user_ids['analyst1'] if idx % 2 == 0 else user_ids['analyst2']
        
        # Calculate due date & ageing
        created_dt = datetime.now() - timedelta(days=idx % 8)
        due_hours = 4 if exc['priority'] == 'Critical' else (24 if exc['priority'] == 'High' else 72)
        due_dt = created_dt + timedelta(hours=due_hours)
        
        sla_st = 'Within SLA'
        if datetime.now() > due_dt:
            sla_st = 'SLA Breached'
        elif (due_dt - datetime.now()).total_seconds() < 7200:
            sla_st = 'At Risk'
            
        approval_st = 'Not Required'
        if status in ['Pending Approval', 'Resolved', 'Closed']:
            approval_st = 'Pending Approval' if status == 'Pending Approval' else 'Approved'

        cursor.execute("""
            UPDATE exceptions 
            SET status = ?, owner_id = ?, created_at = ?, due_date = ?, sla_status = ?, approval_status = ?,
                root_cause = 'Timing lag in bank clearance feed', resolution_summary = 'Verified receipt with Chase online portal.'
            WHERE id = ?
        """, (status, assigned_owner, created_dt.strftime('%Y-%m-%d %H:%M:%S'), due_dt.strftime('%Y-%m-%d %H:%M:%S'), sla_st, approval_st, exc['id']))
        
        # Add sample comment
        cursor.execute("""
            INSERT INTO exception_comments (exception_id, user_id, comment, created_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (exc['id'], assigned_owner, f"Investigating discrepancy of {exc['currency']} {exc['amount']:,.2f}. Contacted clearing team."))
        
        # If Pending Approval, create an approval request
        if status == 'Pending Approval':
            cursor.execute("""
                INSERT INTO approvals (exception_id, requested_by, proposed_resolution, status, comments)
                VALUES (?, ?, 'Fee deduction of $150 posted to Bank Charges Ledger.', 'Pending Approval', 'Requires manager sign-off for fee write-off.')
            """, (exc['id'], assigned_owner))

    # 10. Seed Initial Audit Logs
    cursor.execute("""
        INSERT INTO audit_logs (user_id, username, action, entity, record_id, previous_value_json, new_value_json, ip_address, reason)
        VALUES (?, 'admin', 'SYSTEM_INITIALIZATION', 'system', '1', NULL, '{"status": "Initialized"}', '127.0.0.1', 'Initial database seed')
    """, (user_ids['admin'],))

    conn.commit()
    conn.close()
    print("Database seeding completed successfully!")

if __name__ == '__main__':
    seed_database()
