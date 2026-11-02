import os
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from kavosh.schema import init_db
from kavosh.seeder import seed_curriculum


class TestAllGradesSeed(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        init_db(self.conn)
        seed_curriculum(self.conn)

    def test_all_six_grades_and_31_lessons_present(self):
        cur = self.conn.cursor()
        expected = {7: 8, 8: 7, 9: 6, 10: 4, 11: 3, 12: 3}
        for grade, lesson_count in expected.items():
            cur.execute("SELECT COUNT(*) FROM lessons WHERE grade = ?", (grade,))
            self.assertEqual(
                cur.fetchone()[0], lesson_count, f"Grade {grade} lesson count mismatch"
            )

    def test_vocabulary_per_grade_populated(self):
        cur = self.conn.cursor()
        for grade in range(7, 13):
            cur.execute("SELECT COUNT(*) FROM vocabulary WHERE grade = ?", (grade,))
            count = cur.fetchone()[0]
            self.assertGreaterEqual(
                count, 50, f"Grade {grade} has too few words ({count})"
            )

    def test_rubrics_for_all_grades(self):
        cur = self.conn.cursor()
        for grade in range(7, 13):
            cur.execute("SELECT COUNT(*) FROM rubrics WHERE grade = ?", (grade,))
            self.assertGreaterEqual(
                cur.fetchone()[0], 2, f"Missing rubrics for Grade {grade}"
            )

    def test_passages_populated(self):
        cur = self.conn.cursor()
        for grade in range(7, 13):
            cur.execute(
                "SELECT COUNT(*) FROM passages_fts WHERE grade = ?", (str(grade),)
            )
            self.assertGreaterEqual(
                cur.fetchone()[0], 1, f"Missing passages for Grade {grade}"
            )


if __name__ == "__main__":
    unittest.main()
