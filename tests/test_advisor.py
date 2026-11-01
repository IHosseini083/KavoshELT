import sqlite3
import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from schema import init_db
from seed_all_grades import seed_curriculum
from advisor import analyze_and_advise

class TestAdvisor(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        init_db(self.conn)
        seed_curriculum(self.conn)

    def test_grade7_flags_advanced_words_and_suggests_alternatives(self):
        text = "The physician helped the patient."
        res = analyze_and_advise(self.conn, max_grade=7, max_lesson=8, text=text)
        self.assertFalse(res["is_valid"])
        self.assertIn("physician", res["out_of_syllabus_words"])
        diag = res["word_diagnostics"].get("physician", {})
        self.assertEqual(diag.get("taught_in_grade"), 10)
        self.assertIn("doctor", diag.get("in_syllabus_alternatives", []))

    def test_grade11_allows_present_perfect_grade10_forbids(self):
        text = "She has lived in Shiraz for five years."
        res10 = analyze_and_advise(self.conn, max_grade=10, max_lesson=4, text=text)
        res11 = analyze_and_advise(self.conn, max_grade=11, max_lesson=2, text=text)
        self.assertFalse(res10["is_valid"])
        self.assertTrue(res11["is_valid"])

    def test_grade12_allows_passive_grade11_forbids(self):
        text = "The new hospital was built by Dr. Gharib."
        res11 = analyze_and_advise(self.conn, max_grade=11, max_lesson=3, text=text)
        res12 = analyze_and_advise(self.conn, max_grade=12, max_lesson=1, text=text)
        self.assertFalse(res11["is_valid"])
        self.assertTrue(res12["is_valid"])

if __name__ == "__main__":
    unittest.main()
