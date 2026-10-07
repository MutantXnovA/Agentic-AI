import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from rule_engine import evaluate_pair, normalize_reference, fuzzy_ratio

class TestReconciliationMatchingEngine(unittest.TestCase):

    def test_normalize_reference(self):
        self.assertEqual(normalize_reference('REF12345'), '12345')
        self.assertEqual(normalize_reference('PAY-12345'), '12345')
        self.assertEqual(normalize_reference('INV_9941-A'), '9941A')
        self.assertEqual(normalize_reference(None), '')

    def test_fuzzy_ratio(self):
        sim = fuzzy_ratio('Acme Global Corp Inc', 'Acme Global Corporation')
        self.assertGreaterEqual(sim, 80.0)

    def test_evaluate_pair_exact_match(self):
        rule = {
            'match_fields': ['external_txn_id', 'amount'],
            'date_tolerance_days': 0,
            'amount_tolerance': 0.0,
            'currency_tolerance': 1
        }
        txn_a = {'external_txn_id': 'TXN-100', 'amount': 5000.0, 'currency': 'USD', 'txn_date': '2026-10-01 10:00:00'}
        txn_b = {'external_txn_id': 'TXN-100', 'amount': 5000.0, 'currency': 'USD', 'txn_date': '2026-10-01 10:00:00'}
        
        is_match, score, diff = evaluate_pair(txn_a, txn_b, rule)
        self.assertTrue(is_match)
        self.assertEqual(score, 100.0)
        self.assertEqual(diff['amount_diff'], 0.0)

    def test_evaluate_pair_amount_tolerance(self):
        rule = {
            'match_fields': ['ref_number', 'amount'],
            'date_tolerance_days': 1,
            'amount_tolerance': 50.0,
            'currency_tolerance': 1
        }
        txn_a = {'ref_number': 'PAY-901', 'amount': 1000.0, 'currency': 'USD', 'txn_date': '2026-10-01 10:00:00'}
        txn_b = {'ref_number': 'PAY-901', 'amount': 975.0, 'currency': 'USD', 'txn_date': '2026-10-02 10:00:00'}
        
        is_match, score, diff = evaluate_pair(txn_a, txn_b, rule)
        self.assertTrue(is_match)
        self.assertEqual(diff['amount_diff'], 25.0)

    def test_evaluate_pair_date_mismatch_out_of_tolerance(self):
        rule = {
            'match_fields': ['ref_number', 'txn_date'],
            'date_tolerance_days': 1,
            'amount_tolerance': 0.0,
            'currency_tolerance': 1
        }
        txn_a = {'ref_number': 'PAY-901', 'amount': 1000.0, 'currency': 'USD', 'txn_date': '2026-10-01 10:00:00'}
        txn_b = {'ref_number': 'PAY-901', 'amount': 1000.0, 'currency': 'USD', 'txn_date': '2026-10-05 10:00:00'}
        
        is_match, score, diff = evaluate_pair(txn_a, txn_b, rule)
        self.assertFalse(is_match)

if __name__ == '__main__':
    unittest.main()
