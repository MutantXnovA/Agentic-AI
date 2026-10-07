import sys
import os
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from exception_engine import calculate_priority_and_sla, get_ageing_bucket

class TestExceptionWorkflow(unittest.TestCase):

    def test_priority_and_sla_critical(self):
        priority, severity, due_date = calculate_priority_and_sla('Failed Payment', 15000.0)
        self.assertEqual(priority, 'Critical')
        self.assertEqual(severity, 'Critical')
        expected_due = datetime.now() + timedelta(hours=4)
        self.assertAlmostEqual((due_date - expected_due).total_seconds(), 0, delta=10)

    def test_priority_and_sla_low(self):
        priority, severity, due_date = calculate_priority_and_sla('Timing Difference', 45.0)
        self.assertEqual(priority, 'Low')
        expected_due = datetime.now() + timedelta(days=7)
        self.assertAlmostEqual((due_date - expected_due).total_seconds(), 0, delta=10)

    def test_ageing_bucket_mapping(self):
        self.assertEqual(get_ageing_bucket(0), '0–1 Days')
        self.assertEqual(get_ageing_bucket(2), '2–3 Days')
        self.assertEqual(get_ageing_bucket(5), '4–7 Days')
        self.assertEqual(get_ageing_bucket(12), '8–15 Days')
        self.assertEqual(get_ageing_bucket(25), '16–30 Days')
        self.assertEqual(get_ageing_bucket(45), '30+ Days')

if __name__ == '__main__':
    unittest.main()
