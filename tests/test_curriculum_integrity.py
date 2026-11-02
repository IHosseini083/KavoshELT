from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from typing import Any

from sqlalchemy import select

from kavosh.integrity import (
    EXPECTED_LESSONS,
    format_coverage_table,
    run_integrity_audit,
)
from kavosh.models import ConceptNode, ExamQuestionItem, Lesson, session_scope
from kavosh.paths import datasets_dir
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

    def test_every_mcq_has_distractor_notes(self) -> None:
        codes = {w["code"] for w in self.report["warnings"]}
        self.assertNotIn("missing_distractor_notes", codes)
        bank = self.report["coverage"]["exam_bank"]
        self.assertEqual(
            bank["multiple_choice_with_distractor_notes"], bank["multiple_choice"]
        )
        self.assertEqual(bank["distractor_notes_by_status"]["machine_drafted"], 162)
        self.assertEqual(bank["distractor_notes_by_status"]["authored"], 135)

    def test_machine_drafted_notes_discuss_every_wrong_option(self) -> None:
        with session_scope(self.conn) as session:
            drafted = list(
                session.scalars(
                    select(ExamQuestionItem).where(
                        ExamQuestionItem.distractor_status == "machine_drafted"
                    )
                ).all()
            )
        self.assertEqual(len(drafted), 162)
        for item in drafted:
            options = json.loads(item.options_json or "[]")
            wrong = [o.split(") ", 1)[1] for o in options if o != item.canonical_answer]
            self.assertEqual(len(wrong), 3, item.id)
            notes = (item.distractor_analysis or "").lower()
            for text_ in wrong:
                self.assertIn(text_.lower(), notes, item.id)

    def test_authentic_exam_file_has_no_machine_drafted_content(self) -> None:
        path = datasets_dir() / "national_exams_grade12_1397_1405.json"
        items = json.loads(path.read_text(encoding="utf-8"))["items"]
        self.assertFalse([i["id"] for i in items if "distractor_status" in i])

    def test_unmatched_draft_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for src in datasets_dir().glob("*.json"):
                shutil.copy(src, tmp)
            drafts = Path(tmp) / "distractor_drafts_grade12.json"
            doc = json.loads(drafts.read_text(encoding="utf-8"))
            doc["drafts"].append({**doc["drafts"][0], "stem_text": "No such stem"})
            drafts.write_text(json.dumps(doc), encoding="utf-8")
            conn = sqlite3.connect(":memory:")
            init_db(conn)
            with self.assertRaisesRegex(ValueError, "match no exam item"):
                seed_curriculum(conn, tmp)
            conn.close()

    def test_prerequisite_edges_resolve_to_lower_grade_nodes(self) -> None:
        codes = {w["code"] for w in self.report["warnings"]}
        self.assertNotIn("external_edge_target", codes)
        graph = self.report["coverage"]["concept_graph"]
        self.assertEqual(graph["edges_to_unseeded_nodes"], 0)
        expected = {
            "g9.l5.grammar.simple_past": (9, 5),
            "g10.l4.grammar.modals": (10, 4),
            "g11.l1.grammar.present_perfect": (11, 1),
            "g11.l2.grammar.conditional_type_1": (11, 2),
        }
        with session_scope(self.conn) as session:
            for node_id, (grade, lesson) in expected.items():
                node = session.get(ConceptNode, node_id)
                self.assertIsNotNone(node, node_id)
                assert node is not None
                self.assertEqual((node.grade, node.lesson_num), (grade, lesson))
                self.assertEqual(node.category, "grammar")
                self.assertTrue(node.title_fa and node.description)
                self.assertTrue(
                    session.scalar(
                        select(Lesson).where(
                            Lesson.grade == grade, Lesson.lesson_num == lesson
                        )
                    )
                )

    def test_coverage_report_lists_every_lesson(self) -> None:
        rows = self.report["coverage"]["lessons"]
        self.assertEqual(len(rows), 31)
        self.assertEqual({(r["grade"], r["lesson"]) for r in rows}, self._lesson_keys())
        for row in rows:
            self.assertGreater(row["vocabulary"], 0)
            self.assertEqual(row["conversation"], 1)
            self.assertEqual(row["reading"], 1)
            self.assertIn("no_listening_script", row["flags"])
        self.assertEqual(
            self.report["coverage"]["flag_summary"]["no_listening_script"], 31
        )

    def test_coverage_table_renders(self) -> None:
        table = format_coverage_table(self.report)
        self.assertIn("| 12 | 3 | Renewable Energy |", table)
        self.assertIn("297/297 MCQs", table)

    def _lesson_keys(self) -> set[tuple[int, int]]:
        with session_scope(self.conn) as session:
            return {
                (les.grade, les.lesson_num)
                for les in session.scalars(select(Lesson)).all()
            }

    def test_audit_rejects_bad_distractor_status(self) -> None:
        from sqlalchemy import text

        conn = sqlite3.connect(":memory:")
        init_db(conn)
        seed_curriculum(conn)
        with session_scope(conn) as session:
            session.execute(
                text(
                    "UPDATE exam_question_items SET distractor_status = 'bogus' "
                    "WHERE id = (SELECT id FROM exam_question_items LIMIT 1)"
                )
            )
            session.execute(
                text(
                    "UPDATE exam_question_items SET distractor_status = 'machine_drafted', "
                    "distractor_analysis = NULL WHERE id = ("
                    "SELECT id FROM exam_question_items ORDER BY id DESC LIMIT 1)"
                )
            )
        report = run_integrity_audit(conn)
        conn.close()
        messages = [
            e["message"] for e in report["errors"] if e["code"] == "distractor_status"
        ]
        self.assertEqual(len(messages), 2, messages)

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
