import os
import csv
import json
import uuid
from flask import Blueprint, request, jsonify, g
from werkzeug.utils import secure_filename
from auth import require_auth, require_role
from database import get_db
from audit import log_audit_event
from config import Config

ingestion_bp = Blueprint('ingestion', __name__, url_prefix='/api/ingestion')

ALLOWED_EXTENSIONS = {'csv', 'json', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@ingestion_bp.route('/preview', methods=['POST'])
@require_auth
@require_role([Config.ROLE_SUPER_ADMIN, Config.ROLE_FINANCE_ADMIN, Config.ROLE_FINANCE_MANAGER, Config.ROLE_RECON_ANALYST])
def preview_file():
    """
    Step 1: Upload file for structural validation and column header preview.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request.'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected.'}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        temp_path = os.path.join(Config.UPLOAD_FOLDER, f"temp_{uuid.uuid4().hex}_{filename}")
        file.save(temp_path)
        
        headers = []
        preview_rows = []
        total_lines = 0
        
        try:
            with open(temp_path, mode='r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                headers = next(reader, [])
                for idx, row in enumerate(reader):
                    if idx < 5:
                        preview_rows.append(row)
                    total_lines += 1
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify({'error': f'Failed to parse CSV file: {str(e)}'}), 400

        return jsonify({
            'temp_file_path': temp_path,
            'filename': filename,
            'headers': headers,
            'sample_rows': preview_rows,
            'estimated_records': total_lines
        })
        
    return jsonify({'error': 'Invalid file format. Only CSV or JSON files are supported.'}), 400

@ingestion_bp.route('/confirm', methods=['POST'])
@require_auth
@require_role([Config.ROLE_SUPER_ADMIN, Config.ROLE_FINANCE_ADMIN, Config.ROLE_FINANCE_MANAGER, Config.ROLE_RECON_ANALYST])
def confirm_import():
    """
    Step 2: Map columns, validate rules (missing fields, dates, amounts, duplicates), insert transactions.
    Returns complete import summary (Received, Accepted, Rejected, Duplicates, Validation Errors).
    """
    data = request.json or {}
    temp_path = data.get('temp_file_path')
    source_id = data.get('source_id')
    account_id = data.get('account_id')
    entity_id = data.get('entity_id')
    mapping = data.get('mapping', {}) # e.g. {'external_txn_id': 'Transaction ID', 'amount': 'Amount', ...}
    
    if not temp_path or not os.path.exists(temp_path):
        return jsonify({'error': 'Uploaded preview session expired or file not found.'}), 400
        
    if not source_id or not mapping:
        return jsonify({'error': 'Source ID and field mapping are required.'}), 400

    conn = get_db()
    cursor = conn.cursor()
    
    # Create Import Batch record
    batch_code = f"BATCH-{uuid.uuid4().hex[:8].upper()}"
    filename = os.path.basename(temp_path)
    
    cursor.execute("""
        INSERT INTO import_batches (batch_code, source_id, filename, uploaded_by)
        VALUES (?, ?, ?, ?)
    """, (batch_code, source_id, filename, g.current_user['id']))
    batch_id = cursor.lastrowid
    
    records_received = 0
    records_accepted = 0
    records_rejected = 0
    duplicates_count = 0
    errors = []
    
    # Get existing external_txn_ids to check duplicates
    cursor.execute("SELECT external_txn_id FROM transactions WHERE source_id = ?", (source_id,))
    existing_ext_ids = set(row['external_txn_id'] for row in cursor.fetchall())

    with open(temp_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, start=1):
            records_received += 1
            row_errors = []
            
            # Map values
            ext_id = row.get(mapping.get('external_txn_id', '')).strip() if mapping.get('external_txn_id') in row else None
            ref_num = row.get(mapping.get('ref_number', '')).strip() if mapping.get('ref_number') in row else None
            txn_date = row.get(mapping.get('txn_date', '')).strip() if mapping.get('txn_date') in row else None
            amount_str = row.get(mapping.get('amount', '')).strip() if mapping.get('amount') in row else None
            currency = row.get(mapping.get('currency', 'USD')).strip() if mapping.get('currency') in row else 'USD'
            counterparty = row.get(mapping.get('counterparty', '')).strip() if mapping.get('counterparty') in row else ''
            description = row.get(mapping.get('description', '')).strip() if mapping.get('description') in row else ''
            debit_credit = row.get(mapping.get('debit_credit', 'Credit')).strip() if mapping.get('debit_credit') in row else 'Credit'
            
            # Validation Checks
            if not ext_id:
                row_errors.append(f"Row {row_num}: Missing mandatory Transaction ID.")
            elif ext_id in existing_ext_ids:
                duplicates_count += 1
                row_errors.append(f"Row {row_num}: Duplicate Transaction ID '{ext_id}'.")

            if not amount_str:
                row_errors.append(f"Row {row_num}: Missing mandatory Amount.")
            else:
                try:
                    amount_val = float(amount_str.replace(',', '').replace('$', '').replace('₹', ''))
                    if amount_val <= 0:
                        row_errors.append(f"Row {row_num}: Invalid zero or negative amount '{amount_str}'.")
                except ValueError:
                    row_errors.append(f"Row {row_num}: Non-numeric amount value '{amount_str}'.")

            if row_errors:
                records_rejected += 1
                errors.append({"row": row_num, "reasons": row_errors})
                continue
                
            # If clean, insert transaction
            try:
                cursor.execute("""
                    INSERT INTO transactions (batch_id, external_txn_id, ref_number, txn_date, amount, currency, debit_credit, account_id, entity_id, description, counterparty, source_id, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
                """, (batch_id, ext_id, ref_num, txn_date, amount_val, currency, debit_credit, account_id, entity_id, description, counterparty, source_id))
                existing_ext_ids.add(ext_id)
                records_accepted += 1
            except Exception as e:
                records_rejected += 1
                errors.append({"row": row_num, "reasons": [f"Database error: {str(e)}"]})

    # Update Batch Summary
    cursor.execute("""
        UPDATE import_batches 
        SET total_records = ?, accepted_records = ?, rejected_records = ?, duplicate_records = ?, errors_json = ?
        WHERE id = ?
    """, (records_received, records_accepted, records_rejected, duplicates_count, json.dumps(errors[:50]), batch_id))

    conn.commit()
    conn.close()
    
    # Clean up temp file
    if os.path.exists(temp_path):
        os.remove(temp_path)

    log_audit_event(
        action='IMPORT_TRANSACTIONS_BATCH',
        entity='import_batches',
        record_id=str(batch_id),
        new_value={
            'batch_code': batch_code,
            'accepted': records_accepted,
            'rejected': records_rejected,
            'duplicates': duplicates_count
        }
    )

    return jsonify({
        'message': 'File processed successfully',
        'summary': {
            'batch_code': batch_code,
            'records_received': records_received,
            'records_accepted': records_accepted,
            'records_rejected': records_rejected,
            'duplicate_records': duplicates_count,
            'errors': errors[:20] # Return top 20 error details
        }
    })
