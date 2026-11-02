from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest

from kavosh.composer import compose_exam, swap_slot_item
from kavosh.schema import init_db
from kavosh.seeder import seed_curriculum


class TestExamComposer(unittest.TestCase):
    conn: sqlite3.Connection
    tmp_dir: tempfile.TemporaryDirectory[str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.conn = sqlite3.connect(":memory:")
        init_db(cls.conn)
        seed_curriculum(cls.conn)
        cls.tmp_dir = tempfile.TemporaryDirectory()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp_dir.cleanup()
        cls.conn.close()

    def test_mode_1_full_mock_national_exam(self) -> None:
        result = compose_exam(
            self.conn,
            mode="full_mock",
            grade=12,
            target_points=28.0,
            sourcing="past_papers",
            school_name="دبیرستان نمونه",
            teacher_name="گروه آموزشی زبان",
            out_dir=os.path.join(self.tmp_dir.name, "m1"),
        )
        self.assertEqual(result["mode"], "full_mock")
        self.assertAlmostEqual(result["total_points"], 28.0, places=3)
        self.assertEqual(len(result["sections"]), 5)
        sections = {sec["section_code"] for sec in result["sections"]}
        self.assertEqual(
            sections, {"vocabulary", "grammar", "writing", "cloze", "reading"}
        )

        self.assertTrue(os.path.exists(result["student_pdf"]))
        self.assertTrue(os.path.exists(result["student_docx"]))
        self.assertTrue(os.path.exists(result["answer_key_pdf"]))

    def test_mode_2_skill_worksheet(self) -> None:
        result = compose_exam(
            self.conn,
            mode="skill_worksheet",
            grade=12,
            section="writing",
            target_points=6.0,
            sourcing="hybrid",
            out_dir=os.path.join(self.tmp_dir.name, "m2"),
        )
        self.assertEqual(result["mode"], "skill_worksheet")
        self.assertAlmostEqual(result["total_points"], 6.0, places=3)
        self.assertEqual(len(result["sections"]), 1)
        self.assertEqual(result["sections"][0]["section_code"], "writing")

    def test_mode_3_custom_quiz_ai_twins(self) -> None:
        result = compose_exam(
            self.conn,
            mode="custom_quiz",
            grade=12,
            lessons=[1],
            target_points=10.0,
            sourcing="ai_twins",
            out_dir=os.path.join(self.tmp_dir.name, "m3"),
        )
        self.assertEqual(result["mode"], "custom_quiz")
        self.assertAlmostEqual(result["total_points"], 10.0, places=3)
        for sec in result["sections"]:
            for it in sec["items"]:
                self.assertEqual(it["lesson_num"], 1)
                self.assertTrue(it["is_synthetic_twin"])

    def test_mode_4_interactive_slot_swap(self) -> None:
        mock_exam = compose_exam(
            self.conn,
            mode="full_mock",
            grade=12,
            target_points=28.0,
            sourcing="past_papers",
            out_dir=os.path.join(self.tmp_dir.name, "m4"),
        )
        original_item = mock_exam["sections"][1]["items"][0]
        slot_id = original_item["id"]

        swapped_exam = swap_slot_item(self.conn, mock_exam, slot_id)
        new_item = swapped_exam["sections"][1]["items"][0]
        self.assertNotEqual(new_item["id"], slot_id)
        self.assertEqual(new_item["points"], original_item["points"])
        self.assertAlmostEqual(swapped_exam["total_points"], 28.0, places=3)


if __name__ == "__main__":
    unittest.main()
