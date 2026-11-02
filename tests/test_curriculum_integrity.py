from __future__ import annotations

import sqlite3
import unittest
from typing import Any

from kavosh.integrity import EXPECTED_LESSONS, run_integrity_audit
from kavosh.schema import init_db
from kavosh.seeder import seed_curriculum


class TestCurriculumIntegrity(unittest.TestCase):
    conn: sqlite3.Connection
    report: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.conn = sqlite3.connect(":memory:")
        init_db(cls.conn)
        seed_curriculum(cls.conn)
        cls.report = run_integrity_audit(cls.conn)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.conn.close()

    def test_no_structural_errors(self) -> None:
        self.assertEqual(self.report["errors"], [])
        self.assertTrue(self.report["passed"])

    def test_counts_cover_six_grades_31_lessons_and_27_papers(self) -> None:
        counts = self.report["counts"]
        self.assertEqual(counts["lessons"], sum(EXPECTED_LESSONS.values()))
        self.assertEqual(counts["lessons"], 31)
        self.assertEqual(counts["exam_papers"], 27)
        self.assertEqual(counts["exam_items"], 702)
        self.assertGreater(counts["l1_patterns"], 0)

    def test_every_lesson_has_vocabulary_and_passages(self) -> None:
        codes = {w["code"] for w in self.report["warnings"]}
        self.assertNotIn("lesson_without_vocabulary", codes)
        missing = [
            w
            for w in self.report["warnings"]
            if w["code"] == "lesson_missing_passage" and "listening" not in w["message"]
        ]
        self.assertEqual(missing, [])

    def test_exam_scoring_uses_exact_quarter_points(self) -> None:
        bad = {"points_granularity", "rubric_granularity", "rubric_sum", "paper_total"}
        self.assertFalse(bad & {e["code"] for e in self.report["errors"]})

    def test_audit_detects_orphans(self) -> None:
        from sqlalchemy import text

        from kavosh.models import session_scope

        conn = sqlite3.connect(":memory:")
        init_db(conn)
        seed_curriculum(conn)
        with session_scope(conn) as session:
            session.execute(
                text(
                    "INSERT INTO vocabulary (word, lemma, pos, grade, lesson_num) "
                    "VALUES ('ghost', 'ghost', 'noun', 7, 99)"
                )
            )
        report = run_integrity_audit(conn)
        conn.close()
        self.assertIn("orphan_vocabulary", {e["code"] for e in report["errors"]})


if __name__ == "__main__":
    unittest.main()
