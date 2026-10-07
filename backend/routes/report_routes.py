import csv
import io
from flask import Blueprint, request, jsonify, Response
from auth import require_auth
from database import get_db

report_bp = Blueprint('reports', __name__, url_prefix='/api/reports')

@report_bp.route('/dashboard', methods=['GET'])
@require_auth
def get_dashboard_summary():
    """
    Returns enterprise dashboard KPI metrics, filters, and multi-chart dataset.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # KPI Metrics
    cursor.execute("SELECT COUNT(*) as total, SUM(amount) as total_value FROM transactions")
    txn_stats = cursor.fetchone()
    
    cursor.execute("SELECT COUNT(*) as matched_count FROM transactions WHERE is_matched = 1")
    matched_cnt = cursor.fetchone()['matched_count']
    
    cursor.execute("SELECT COUNT(*) as unmatched_count FROM transactions WHERE is_matched = 0")
    unmatched_cnt = cursor.fetchone()['unmatched_count']
    
    cursor.execute("SELECT COUNT(*) as total_exc, COUNT(CASE WHEN priority = 'Critical' THEN 1 END) as critical_cnt, COUNT(CASE WHEN status IN ('Resolved', 'Closed') THEN 1 END) as resolved_cnt, COUNT(CASE WHEN status NOT IN ('Resolved', 'Closed') THEN 1 END) as open_cnt FROM exceptions")
    exc_stats = cursor.fetchone()

    # Chart 1: Reconciliation Status Breakdown
    cursor.execute("""
        SELECT match_status, COUNT(*) as count 
        FROM reconciliation_results 
        GROUP BY match_status
    """)
    recon_status_chart = [dict(row) for row in cursor.fetchall()]

    # Chart 2: Exception Ageing Breakdown
    cursor.execute("""
        SELECT 
            CASE 
                WHEN ageing_days <= 1 THEN '0–1 Days'
                WHEN ageing_days <= 3 THEN '2–3 Days'
                WHEN ageing_days <= 7 THEN '4–7 Days'
                WHEN ageing_days <= 15 THEN '8–15 Days'
                WHEN ageing_days <= 30 THEN '16–30 Days'
                ELSE '30+ Days'
            END as bucket,
            COUNT(*) as count
        FROM exceptions
        WHERE status NOT IN ('Closed', 'Resolved')
        GROUP BY bucket
    """)
    ageing_chart = [dict(row) for row in cursor.fetchall()]

    # Chart 3: Exception Priority Breakdown
    cursor.execute("SELECT priority, COUNT(*) as count FROM exceptions GROUP BY priority")
    priority_chart = [dict(row) for row in cursor.fetchall()]

    # Chart 4: Exceptions by Category / Type
    cursor.execute("SELECT exception_type, COUNT(*) as count FROM exceptions GROUP BY exception_type ORDER BY count DESC LIMIT 8")
    category_chart = [dict(row) for row in cursor.fetchall()]

    # Chart 5: Exceptions by Assigned Owner
    cursor.execute("""
        SELECT COALESCE(u.full_name, 'Unassigned') as owner_name, COUNT(e.id) as count
        FROM exceptions e
        LEFT JOIN users u ON e.owner_id = u.id
        GROUP BY owner_name
    """)
    owner_chart = [dict(row) for row in cursor.fetchall()]

    conn.close()

    total_txns = txn_stats['total'] or 1
    recon_rate = round((matched_cnt / total_txns) * 100.0, 1)

    return jsonify({
        'kpis': {
            'total_transactions': txn_stats['total'] or 0,
            'total_transaction_value': round(txn_stats['total_value'] or 0.0, 2),
            'matched_transactions': matched_cnt,
            'unmatched_transactions': unmatched_cnt,
            'reconciliation_rate': recon_rate,
            'total_exceptions': exc_stats['total_exc'] or 0,
            'critical_exceptions': exc_stats['critical_cnt'] or 0,
            'open_exceptions': exc_stats['open_cnt'] or 0,
            'resolved_exceptions': exc_stats['resolved_cnt'] or 0
        },
        'charts': {
            'reconciliation_status': recon_status_chart,
            'ageing_buckets': ageing_chart,
            'priority_breakdown': priority_chart,
            'category_breakdown': category_chart,
            'owner_breakdown': owner_chart
        }
    })

@report_bp.route('/financial-impact', methods=['GET'])
@require_auth
def get_financial_impact_report():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            SUM(amount) as total_discrepancy_value,
            SUM(CASE WHEN status IN ('Resolved', 'Closed') THEN amount ELSE 0 END) as recovered_amount,
            SUM(CASE WHEN status NOT IN ('Resolved', 'Closed') THEN amount ELSE 0 END) as outstanding_amount,
            SUM(CASE WHEN exception_type = 'Bank Fee Difference' AND status IN ('Resolved', 'Closed') THEN amount ELSE 0 END) as writeoffs_amount
        FROM exceptions
    """)
    impact = cursor.fetchone()
    conn.close()
    
    return jsonify({
        'total_discrepancy_value': round(impact['total_discrepancy_value'] or 0.0, 2),
        'recovered_amount': round(impact['recovered_amount'] or 0.0, 2),
        'outstanding_amount': round(impact['outstanding_amount'] or 0.0, 2),
        'writeoffs_amount': round(impact['writeoffs_amount'] or 0.0, 2)
    })

@report_bp.route('/export', methods=['GET'])
@require_auth
def export_report_csv():
    report_type = request.args.get('type', 'transactions')
    conn = get_db()
    cursor = conn.cursor()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    if report_type == 'exceptions':
        cursor.execute("SELECT exception_code, exception_type, description, amount, currency, priority, status, created_at, due_date FROM exceptions")
        rows = cursor.fetchall()
        writer.writerow(['Exception Code', 'Type', 'Description', 'Amount', 'Currency', 'Priority', 'Status', 'Created Date', 'Due Date'])
        for r in rows:
            writer.writerow(list(r))
    else:
        cursor.execute("SELECT external_txn_id, ref_number, txn_date, amount, currency, debit_credit, counterparty, status FROM transactions LIMIT 500")
        rows = cursor.fetchall()
        writer.writerow(['Txn ID', 'Reference', 'Date', 'Amount', 'Currency', 'Debit/Credit', 'Counterparty', 'Match Status'])
        for r in rows:
            writer.writerow(list(r))
            
    conn.close()
    
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename={report_type}_export.csv'
    return response
