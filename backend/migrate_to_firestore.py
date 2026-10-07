import sqlite3
import json
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase Admin
try:
    firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate('serviceAccountKey.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def migrate_table(conn, table_name):
    print(f"Migrating table {table_name}...")
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT * FROM {table_name}")
    except sqlite3.OperationalError:
        print(f"  Table {table_name} does not exist. Skipping.")
        return
        
    rows = cursor.fetchall()
    print(f"  Found {len(rows)} records.")
    
    batch = db.batch()
    count = 0
    total = 0
    
    for row in rows:
        doc_id = str(row['id'])
        doc_ref = db.collection(table_name).document(doc_id)
        batch.set(doc_ref, row)
        count += 1
        total += 1
        
        if count >= 400: # Firestore batch limit is 500
            batch.commit()
            batch = db.batch()
            count = 0
            print(f"  Committed {total} records...")
            
    if count > 0:
        batch.commit()
        print(f"  Committed {total} records...")
        
    print(f"Finished migrating {table_name}.\n")

def main():
    conn = sqlite3.connect('reconx_financial.db')
    conn.row_factory = dict_factory
    
    tables = [
        'users', 'roles', 'permissions', 'entities', 'accounts', 
        'transaction_sources', 'import_batches', 'transactions', 
        'reconciliation_rules', 'reconciliation_runs', 'reconciliation_results', 
        'exceptions', 'exception_comments', 'exception_attachments', 
        'exception_assignments', 'approvals', 'sla_rules', 'audit_logs', 'notifications'
    ]
    
    for table in tables:
        migrate_table(conn, table)
        
    conn.close()
    print("Migration complete!")

if __name__ == '__main__':
    main()
