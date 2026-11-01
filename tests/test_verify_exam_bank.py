from __future__ import annotations

import json
import sqlite3
import unittest

from models import ConceptNode, ExamQuestionItem, NationalExamPaper, session_scope
from schema import init_db
from seed_all_grades import seed_curriculum
from verify_exam_bank import verify_item, verify_paper


class TestVerifyExamBank(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        init_db(self.conn)
        seed_curriculum(self.conn)

        with session_scope(self.conn) as session:
            existing_paper = session.get(NationalExamPaper, "paper_1402_khordad")
            if not existing_paper:
                paper = NationalExamPaper(
                    id="paper_1402_khordad",
                    grade=12,
                    shamsi_year=1402,
                    session="Khordad",
                    total_written_points=28.0,
                    blueprint_version="1402-1405_conceptual",
                    source_origin="Markaz-e-Sanjesh",
                    is_verified=True,
                )
                session.add(paper)
                session.commit()

    def tearDown(self) -> None:
        self.conn.close()

    def test_v1_point_precision_violation(self) -> None:
        item = ExamQuestionItem(
            id="item_v1_fail",
            paper_id="paper_1402_khordad",
            section_code="grammar",
            item_type="multiple_choice",
            grade=12,
            lesson_num=1,
            points=0.33,  # Invalid: not multiple of 0.25
            instruction_en="Choose the correct answer.",
            stem_text="The bridge was built in 1602.",
            canonical_answer="built",
            options_json='["built", "build"]',
            rubric_breakdown_json='{"answer": 0.33}',
            concept_ids_json='["g12.l1.grammar.passive_voice"]',
        )
        report = verify_item(self.conn, item)
        self.assertFalse(report["is_valid"])
        self.assertTrue(any("0.25" in err for err in report["errors"]))

    def test_v1_rubric_sum_mismatch(self) -> None:
        item = ExamQuestionItem(
            id="item_v1_sum_fail",
            paper_id="paper_1402_khordad",
            section_code="writing",
            item_type="paragraph_writing",
            grade=12,
            lesson_num=1,
            points=2.0,
            instruction_en="Write a paragraph.",
            stem_text="Write about helping parents.",
            canonical_answer="Sample paragraph",
            rubric_breakdown_json='{"topic_sentence": 0.5, "supporting_sentences": 0.75}',  # Sum = 1.25 != 2.0
            concept_ids_json='["g12.l1.grammar.passive_voice"]',
        )
        report = verify_item(self.conn, item)
        self.assertFalse(report["is_valid"])
        self.assertTrue(
            any("rubric breakdown sum" in err.lower() for err in report["errors"])
        )

    def test_v2_syllabus_alignment_violation(self) -> None:
        item = ExamQuestionItem(
            id="item_v2_fail",
            paper_id="paper_1402_khordad",
            section_code="vocabulary",
            item_type="fill_blank",
            grade=12,
            lesson_num=1,
            points=1.0,
            instruction_en="Complete the sentence.",
            stem_text="The quantum physics spectrometer malfunctioned during the astrophysics experiment.",  # Complex out-of-syllabus words
            canonical_answer="spectrometer",
            rubric_breakdown_json='{"answer": 1.0}',
            concept_ids_json='["g12.l1.grammar.passive_voice"]',
        )
        report = verify_item(self.conn, item)
        self.assertFalse(report["is_valid"])
        self.assertTrue(
            any("out-of-syllabus" in err.lower() for err in report["errors"])
        )

    def test_v3_concept_graph_integrity_violation(self) -> None:
        item = ExamQuestionItem(
            id="item_v3_fail",
            paper_id="paper_1402_khordad",
            section_code="grammar",
            item_type="multiple_choice",
            grade=12,
            lesson_num=1,
            points=0.5,
            instruction_en="Choose the correct answer.",
            stem_text="The book was written by Hafez.",
            canonical_answer="written",
            options_json='["written", "wrote"]',
            rubric_breakdown_json='{"answer": 0.5}',
            concept_ids_json='["non_existent_concept_id"]',  # Missing node
        )
        report = verify_item(self.conn, item)
        self.assertFalse(report["is_valid"])
        self.assertTrue(any("concept node" in err.lower() for err in report["errors"]))

    def test_v4_answer_key_mc_missing_answer_violation(self) -> None:
        item = ExamQuestionItem(
            id="item_v4_fail",
            paper_id="paper_1402_khordad",
            section_code="grammar",
            item_type="multiple_choice",
            grade=12,
            lesson_num=1,
            points=0.5,
            instruction_en="Choose the correct answer.",
            stem_text="The book was written by Hafez.",
            canonical_answer="c) published",  # Not in options
            options_json='["a) written", "b) wrote"]',
            rubric_breakdown_json='{"answer": 0.5}',
            concept_ids_json='["g12.l1.grammar.passive_voice"]',
        )
        report = verify_item(self.conn, item)
        self.assertFalse(report["is_valid"])
        self.assertTrue(
            any("canonical answer" in err.lower() for err in report["errors"])
        )

    def test_valid_item_passes_all_checks(self) -> None:
        item = ExamQuestionItem(
            id="item_valid",
            paper_id="paper_1402_khordad",
            section_code="grammar",
            item_type="multiple_choice",
            grade=12,
            lesson_num=1,
            points=0.5,
            instruction_en="Choose the correct answer.",
            stem_text="The book was written by Hafez.",
            canonical_answer="a) written",
            options_json='["a) written", "b) wrote"]',
            rubric_breakdown_json='{"correct_choice": 0.5}',
            concept_ids_json='["g12.l1.grammar.passive_voice"]',
        )
        report = verify_item(self.conn, item)
        self.assertTrue(report["is_valid"], f"Unexpected errors: {report['errors']}")


if __name__ == "__main__":
    unittest.main()
