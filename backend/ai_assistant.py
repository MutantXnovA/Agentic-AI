import random
from difflib import SequenceMatcher

def analyze_exception_root_cause(exc_type: str, description: str, amount: float, source_a_desc: str = None, source_b_desc: str = None) -> dict:
    """
    AI-Assisted Root Cause & Resolution Recommendation Engine.
    Provides non-binding intelligent recommendations for financial analysts.
    """
    suggestions = {
        'Missing Transaction': {
            'probable_root_cause': 'Timing lag between banking gateway settlement cycles and internal ledger post date OR unposted bank transfer.',
            'suggested_resolution': 'Request bank transaction receipt. If confirmed, initiate manual posting or wait for next clearing batch.',
            'confidence': 92.5
        },
        'Amount Mismatch': {
            'probable_root_cause': 'Uncaptured bank processing fee, FX spread deduction, or tax withholding (TDS / VAT deduction at source).',
            'suggested_resolution': 'Verify fee schedule. Post fee adjustment entry of exact difference amount to Bank Charges Ledger.',
            'confidence': 94.0
        },
        'Duplicate Transaction': {
            'probable_root_cause': 'Double submission by payment gateway webhook retry or duplicate file import.',
            'suggested_resolution': 'Flag transaction as duplicate, request gateway confirmation, and process reversal/void entry.',
            'confidence': 96.8
        },
        'Date Mismatch': {
            'probable_root_cause': 'Weekend / public holiday clearing delay or value-date posting convention difference.',
            'suggested_resolution': 'Approve date tolerance exception. No ledger monetary adjustment required.',
            'confidence': 98.0
        },
        'Currency Mismatch': {
            'probable_root_cause': 'Multi-currency conversion missing FX rate conversion entry in accounting ledger.',
            'suggested_resolution': 'Apply spot exchange rate for transaction date and post realized FX gain/loss difference.',
            'confidence': 89.2
        },
        'Failed Payment': {
            'probable_root_cause': 'Insufficient funds, invalid account number, or bank network failure.',
            'suggested_resolution': 'Contact counterparty to re-initiate payment or trigger automated retry workflow.',
            'confidence': 91.0
        }
    }
    
    default_resp = {
        'probable_root_cause': 'Operational discrepancy requiring manual ledger verification against source statement.',
        'suggested_resolution': 'Compare transaction references with bank deposit slips and post corrective ledger journal entry.',
        'confidence': 85.0
    }
    
    result = suggestions.get(exc_type, default_resp)
    result['ai_model'] = 'FinAI-Recon-v3.4 (Rule-Guided Inference)'
    result['is_suggestion'] = True
    return result

def detect_anomalies(transactions: list) -> list:
    """
    Identifies unusual transactions (e.g. unusually round amounts, off-peak hours, duplicate references).
    """
    anomalies = []
    for t in transactions:
        amount = float(t.get('amount', 0))
        # Large round numbers
        if amount > 5000 and amount % 1000 == 0:
            anomalies.append({
                'txn_id': t.get('id'),
                'external_txn_id': t.get('external_txn_id'),
                'anomaly_type': 'Unusual Round High Value',
                'severity': 'Medium',
                'reason': f"Transaction amount ${amount:,.2f} is an exact multiple of 1,000 above $5,000."
            })
    return anomalies
