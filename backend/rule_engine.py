import json
import re
from difflib import SequenceMatcher

def normalize_reference(ref_str: str) -> str:
    """Normalizes reference numbers by removing non-alphanumeric chars and prefixes."""
    if not ref_str:
        return ""
    # Strip common prefixes like PAY-, REF-, TXN-, INV-, spaces, hyphens
    cleaned = re.sub(r'^(PAY|REF|TXN|INV|BANK|SETTLE)[-_\s]*', '', str(ref_str).upper(), flags=re.IGNORECASE)
    return re.sub(r'[^A-Z0-9]', '', cleaned)

def fuzzy_ratio(str1: str, str2: str) -> float:
    """Calculates fuzzy similarity ratio between 0.0 and 100.0 using difflib."""
    if not str1 or not str2:
        return 0.0
    s1 = str(str1).lower().strip()
    s2 = str(str2).lower().strip()
    return SequenceMatcher(None, s1, s2).ratio() * 100.0

def evaluate_pair(txn_a: dict, txn_b: dict, rule: dict) -> tuple[bool, float, dict]:
    """
    Evaluates a single pair of transactions against a specific rule configuration.
    Returns: (is_match, score, diff_details)
    """
    match_fields = rule.get('match_fields', [])
    if isinstance(match_fields, str):
        match_fields = json.loads(match_fields)
        
    date_tol_days = rule.get('date_tolerance_days', 0)
    amount_tol = rule.get('amount_tolerance', 0.0)
    currency_tol = rule.get('currency_tolerance', 1) # 1 means currency must match
    fuzzy_thresh = rule.get('fuzzy_threshold', 85)
    
    diff_details = {
        'amount_diff': abs(float(txn_a['amount']) - float(txn_b['amount'])),
        'date_diff_days': 0,
        'field_scores': {}
    }
    
    # Calculate Date Difference
    try:
        from datetime import datetime
        d_a = datetime.strptime(txn_a['txn_date'][:10], '%Y-%m-%d')
        d_b = datetime.strptime(txn_b['txn_date'][:10], '%Y-%m-%d')
        diff_details['date_diff_days'] = abs((d_a - d_b).days)
    except Exception:
        diff_details['date_diff_days'] = 0

    # 1. Currency Check
    if currency_tol and txn_a['currency'] != txn_b['currency']:
        return False, 0.0, diff_details

    # 2. Debit/Credit Sign Check (Debit matches Credit or same direction depending on multi-source setup)
    # If source A is Bank (+Credit) and Source B is Ledger (+Debit), amounts should match
    
    # 3. Field-by-Field Match Evaluation
    field_match_count = 0
    total_score = 0.0
    
    for field in match_fields:
        if field == 'external_txn_id':
            if txn_a.get('external_txn_id') == txn_b.get('external_txn_id') and txn_a.get('external_txn_id'):
                field_match_count += 1
                total_score += 100.0
            else:
                return False, 0.0, diff_details
                
        elif field == 'ref_number':
            ref_a = normalize_reference(txn_a.get('ref_number'))
            ref_b = normalize_reference(txn_b.get('ref_number'))
            
            if ref_a and ref_b and ref_a == ref_b:
                field_match_count += 1
                total_score += 100.0
            else:
                # Try fuzzy reference match
                sim = fuzzy_ratio(ref_a, ref_b)
                if sim >= fuzzy_thresh:
                    field_match_count += 1
                    total_score += sim
                else:
                    return False, 0.0, diff_details
                    
        elif field == 'amount':
            if diff_details['amount_diff'] <= amount_tol:
                field_match_count += 1
                amt_score = 100.0 if diff_details['amount_diff'] == 0 else max(70.0, 100.0 - (diff_details['amount_diff'] * 10))
                total_score += amt_score
            else:
                return False, 0.0, diff_details
                
        elif field == 'txn_date':
            if diff_details['date_diff_days'] <= date_tol_days:
                field_match_count += 1
                date_score = 100.0 if diff_details['date_diff_days'] == 0 else max(75.0, 100.0 - (diff_details['date_diff_days'] * 10))
                total_score += date_score
            else:
                return False, 0.0, diff_details
                
        elif field == 'counterparty':
            sim = fuzzy_ratio(txn_a.get('counterparty'), txn_b.get('counterparty'))
            if sim >= fuzzy_thresh:
                field_match_count += 1
                total_score += sim
            else:
                return False, 0.0, diff_details

    final_score = round(total_score / len(match_fields), 2) if match_fields else 0.0
    return True, final_score, diff_details
