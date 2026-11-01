import sqlite3
import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from schema import init_db
from seed_all_grades import seed_curriculum
from auditor import run_curriculum_audit

class TestAuditor(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        init_db(self.conn)
        seed_curriculum(self.conn)

    def test_full_curriculum_self_consistency(self):
        report = run_curriculum_audit(self.conn)
        self.assertEqual(report["total_grades"], 6)
        self.assertEqual(report["total_lessons"], 31)
        self.assertEqual(report["passage_validation_failures"], [], f"Passages failed self-validation: {report.get('passage_validation_failures')}")
        self.assertTrue(report["audit_passed"])

if __name__ == "__main__":
    unittest.main()
