from __future__ import annotations

import sqlite3
import unittest
from sqlalchemy import func, select

from models import (
    ConceptEdge,
    ConceptNode,
    ExamQuestionItem,
    L1ErrorPattern,
    NationalExamPaper,
    session_scope,
)
from schema import init_db
from seed_all_grades import seed_curriculum
from verify_exam_bank import audit_national_exam_bank


class TestNationalExamSeed(unittest.TestCase):
    conn: sqlite3.Connection

    @classmethod
    def setUpClass(cls) -> None:
        cls.conn = sqlite3.connect(":memory:")
        init_db(cls.conn)
        seed_curriculum(cls.conn)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.conn.close()

    def test_all_nine_years_and_three_sessions_present(self) -> None:
        with session_scope(self.conn) as session:
            papers = list(session.scalars(select(NationalExamPaper)).all())
            self.assertEqual(len(papers), 27)

            years = sorted(list({p.shamsi_year for p in papers}))
            self.assertEqual(years, list(range(1397, 1406)))

            for yr in range(1397, 1406):
                yr_sessions = {p.session for p in papers if p.shamsi_year == yr}
                self.assertEqual(yr_sessions, {"Khordad", "Shahrivar", "Dey"})

    def test_all_five_sections_and_lessons_populated(self) -> None:
        with session_scope(self.conn) as session:
            items = list(session.scalars(select(ExamQuestionItem)).all())
            self.assertEqual(len(items), 702)  # 27 papers * 26 items

            sections = {it.section_code for it in items}
            self.assertEqual(
                sections, {"vocabulary", "grammar", "writing", "cloze", "reading"}
            )

            lessons = {it.lesson_num for it in items}
            self.assertEqual(lessons, {1, 2, 3})

            difficulties = {it.difficulty for it in items}
            self.assertEqual(difficulties, {"easy", "medium", "hard"})

    def test_concept_graph_nodes_and_edges(self) -> None:
        with session_scope(self.conn) as session:
            nodes = list(session.scalars(select(ConceptNode)).all())
            self.assertGreaterEqual(len(nodes), 14)

            edges = list(session.scalars(select(ConceptEdge)).all())
            self.assertGreaterEqual(len(edges), 5)

            l1_patterns = list(session.scalars(select(L1ErrorPattern)).all())
            self.assertGreaterEqual(len(l1_patterns), 4)

    def test_audit_national_exam_bank_zero_failures(self) -> None:
        report = audit_national_exam_bank(self.conn)
        self.assertTrue(
            report["all_papers_valid"], f"Audit failed: {report.get('failures')}"
        )
        self.assertEqual(report["failed_papers_count"], 0)
        self.assertEqual(report["total_papers"], 27)
        self.assertEqual(report["total_items"], 702)


if __name__ == "__main__":
    unittest.main()
