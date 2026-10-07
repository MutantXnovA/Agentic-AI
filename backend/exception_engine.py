import uuid
import sqlite3
from datetime import datetime, timedelta
from database import get_db

def calculate_priority_and_sla(exc_type: str, amount: float) -> tuple[str, str, datetime]:
    """
    Calculates Exception Priority, Severity, and SLA Due Date.
    """
    amount = abs(float(amount))
    priority = 'Low'
    severity = 'Low'
    
    if amount >= 10000 or exc_type in ['Failed Payment', 'Settlement Difference', 'Duplicate Transaction', 'Overpayment']:
        priority = 'Critical'
        severity = 'Critical'
    elif amount >= 1000 or exc_type in ['Bank Fee Difference', 'Currency Mismatch', 'Unknown Transaction']:
        priority = 'High'
        severity = 'High'
    elif amount >= 100 or exc_type in ['Amount Mismatch', 'Date Mismatch', 'Reference Mismatch', 'Partial Payment']:
        priority = 'Medium'
        severity = 'Medium'
    else:
        priority = 'Low'
        severity = 'Low'
        
    # Calculate SLA due date
    now = datetime.now()
    if priority == 'Critical':
        due_date = now + timedelta(hours=4)
    elif priority == 'High':
        due_date = now + timedelta(hours=24)
    elif priority == 'Medium':
        due_date = now + timedelta(days=3)
    else:
        due_date = now + timedelta(days=7)
        
    return priority, severity, due_date

def get_auto_assignee(conn, department: str = 'Reconciliation') -> int:
    """Selects an active Reconciliation Analyst with lowest assigned exception load."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.id, COUNT(e.id) as load_count 
        FROM users u 
        LEFT JOIN exceptions e ON u.id = e.owner_id AND e.status NOT IN ('Closed', 'Resolved')
        WHERE u.role IN ('reconciliation_analyst', 'finance_manager') AND u.is_active = 1
        GROUP BY u.id
        ORDER BY load_count ASC
        LIMIT 1
    """)
    row = cursor.fetchone()
    return row['id'] if row else 1

def create_exception_for_discrepancy(conn, txn_id: int, recon_res_id: int, exc_type: str, amount: float, currency: str, description: str, owner_id: int = None) -> dict:
    """Creates a structured financial exception record with priority calculation and SLA due date."""
    cursor = conn.cursor()
    
    exc_code = f"EXC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}"
    priority, severity, due_date = calculate_priority_and_sla(exc_type, amount)
    
    if not owner_id:
        try:
            owner_id = get_auto_assignee(conn)
        except Exception:
            owner_id = 1 # Fallback to admin user 1

    cursor.execute("""
        INSERT INTO exceptions (
            exception_code, transaction_id, recon_result_id, exception_type, 
            description, amount, currency, priority, severity, status, 
            owner_id, department, due_date, sla_status, approval_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'New', ?, 'Finance Operations', ?, 'Within SLA', 'Not Required')
    """, (exc_code, txn_id, recon_res_id, exc_type, description, amount, currency, priority, severity, owner_id, due_date.strftime('%Y-%m-%d %H:%M:%S')))
    
    exc_id = cursor.lastrowid
    
    # Notify assigned user
    cursor.execute("""
        INSERT INTO notifications (user_id, title, message, type, link)
        VALUES (?, ?, ?, 'warning', ?)
    """, (owner_id, f"New Exception Assigned: {exc_code}", f"Priority: {priority} - {exc_type} (${amount:,.2f})", f"/exceptions?id={exc_id}"))

    return {
        'id': exc_id,
        'exception_code': exc_code,
        'priority': priority,
        'due_date': due_date.strftime('%Y-%m-%d %H:%M:%S')
    }

def update_sla_statuses():
    """Batch updates SLA Statuses (Within SLA, At Risk, SLA Breached) and ageing days for all open exceptions."""
    conn = None
    try:
        conn = get_db()
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, created_at, due_date, status, priority FROM exceptions WHERE status NOT IN ('Closed', 'Resolved')")
        open_exceptions = cursor.fetchall()
        
        now = datetime.now()
        
        for exc in open_exceptions:
            try:
                created_at = datetime.strptime(exc['created_at'][:19], '%Y-%m-%d %H:%M:%S') if ' ' in exc['created_at'] else datetime.strptime(exc['created_at'][:10], '%Y-%m-%d')
                due_date = datetime.strptime(exc['due_date'][:19], '%Y-%m-%d %H:%M:%S') if ' ' in exc['due_date'] else datetime.strptime(exc['due_date'][:10], '%Y-%m-%d')
            except (ValueError, TypeError):
                continue
            
            ageing_days = (now - created_at).days
            
            sla_status = 'Within SLA'
            if now > due_date:
                sla_status = 'SLA Breached'
            elif (due_date - now).total_seconds() < 7200: # Within 2 hours of breach
                sla_status = 'At Risk'
                
            cursor.execute("UPDATE exceptions SET sla_status = ?, ageing_days = ? WHERE id = ?", (sla_status, ageing_days, exc['id']))
            
        conn.commit()
    except sqlite3.OperationalError as e:
        print(f"[SLA Update] Database busy, skipping SLA refresh: {e}")
    except Exception as e:
        print(f"[SLA Update] Error updating SLA statuses: {e}")
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

def get_ageing_bucket(ageing_days: int) -> str:
    """Returns standard financial exception ageing bucket label."""
    if ageing_days <= 1:
        return '0–1 Days'
    elif ageing_days <= 3:
        return '2–3 Days'
    elif ageing_days <= 7:
        return '4–7 Days'
    elif ageing_days <= 15:
        return '8–15 Days'
    elif ageing_days <= 30:
        return '16–30 Days'
    else:
        return '30+ Days'
