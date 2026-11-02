from __future__ import annotations

import sqlite3
import unittest

from sqlalchemy import select, text

from kavosh.models import (
    ConceptEdge,
    ConceptNode,
    ExamQuestionItem,
    L1ErrorPattern,
    NationalExamPaper,
    session_scope,
)
from kavosh.schema import init_db


class TestGraphModels(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        init_db(self.conn)

    def tearDown(self) -> None:
        self.conn.close()

    def test_concept_node_and_edge_creation(self) -> None:
        with session_scope(self.conn) as session:
            node1 = ConceptNode(
                id="g12.l1.grammar.passive_voice",
                grade=12,
                lesson_num=1,
                category="grammar",
                title_en="Passive Voice (Present & Past Simple)",
                title_fa="ساختار مجهول زمان‌های حال و گذشته ساده",
                description="Object + am/is/are/was/were + past participle",
                embedding_json=None,
            )
            node2 = ConceptNode(
                id="g9.l5.grammar.simple_past",
                grade=9,
                lesson_num=5,
                category="grammar",
                title_en="Simple Past Tense",
                title_fa="زمان گذشته ساده",
                description="Past forms of regular and irregular verbs",
                embedding_json=None,
            )
            session.add_all([node1, node2])
            session.flush()

            edge = ConceptEdge(
                source_id="g12.l1.grammar.passive_voice",
                target_id="g9.l5.grammar.simple_past",
                relation_type="prerequisite_of",
                weight=1.0,
                notes="Learners must master simple past verb forms before mastering past passive.",
            )
            session.add(edge)
            session.commit()

        with session_scope(self.conn) as session:
            retrieved_node = session.get(ConceptNode, "g12.l1.grammar.passive_voice")
            self.assertIsNotNone(retrieved_node)
            assert retrieved_node is not None
            self.assertEqual(retrieved_node.category, "grammar")

            edge_query = select(ConceptEdge).where(
                ConceptEdge.source_id == "g12.l1.grammar.passive_voice"
            )
            edges = list(session.scalars(edge_query).all())
            self.assertEqual(len(edges), 1)
            self.assertEqual(edges[0].target_id, "g9.l5.grammar.simple_past")

    def test_national_exam_paper_and_atomic_question_item(self) -> None:
        with session_scope(self.conn) as session:
            paper = NationalExamPaper(
                id="g12_1402_khordad_standard",
                grade=12,
                shamsi_year=1402,
                session="Khordad",
                total_written_points=28.0,
                blueprint_version="1402-1405_conceptual",
                source_origin="Markaz-e-Sanjesh",
                is_verified=True,
            )
            session.add(paper)
            session.flush()

            q_item = ExamQuestionItem(
                id="g12_1402_khordad_q14",
                paper_id="g12_1402_khordad_standard",
                section_code="grammar",
                item_type="multiple_choice",
                grade=12,
                lesson_num=1,
                bloom_level="apply",
                difficulty="medium",
                points=0.5,
                instruction_en="Choose the correct answer.",
                stem_text="The historic bridge .......... in 1602 by Shah Abbas.",
                passage_text=None,
                options_json='["a) built", "b) was built", "c) has built", "d) is building"]',
                canonical_answer="b) was built",
                acceptable_variants_json='["was built", "b"]',
                rubric_breakdown_json='{"correct_choice": 0.5}',
                distractor_analysis="Distractor a tests passive omission; c tests tense confusion.",
                concept_ids_json='["g12.l1.grammar.passive_voice"]',
                embedding_json=None,
                is_synthetic_twin=False,
                parent_item_id=None,
            )
            session.add(q_item)
            session.commit()

        with session_scope(self.conn) as session:
            retrieved_q = session.get(ExamQuestionItem, "g12_1402_khordad_q14")
            self.assertIsNotNone(retrieved_q)
            assert retrieved_q is not None
            self.assertEqual(retrieved_q.points, 0.5)
            self.assertEqual(retrieved_q.canonical_answer, "b) was built")

    def test_l1_error_pattern_model(self) -> None:
        with session_scope(self.conn) as session:
            err = L1ErrorPattern(
                id="l1_passive_agent_omission",
                concept_id="g12.l1.grammar.passive_voice",
                error_title_fa="حذف فعل to be در جمله مجهول به دلیل تطابق ساختار فارسی",
                incorrect_pattern_en="The book written yesterday.",
                correct_pattern_en="The book was written yesterday.",
                l1_root_cause_fa="در زبان فارسی صفت مفعولی (نوشته شد) گاهی بدون فعل کمکی مناسب ترجمه می‌شود.",
                remedial_drill_template="Identify the missing auxiliary verb in: [stem]",
            )
            session.add(err)
            session.commit()

        with session_scope(self.conn) as session:
            retrieved_err = session.get(L1ErrorPattern, "l1_passive_agent_omission")
            self.assertIsNotNone(retrieved_err)
            assert retrieved_err is not None
            self.assertEqual(retrieved_err.concept_id, "g12.l1.grammar.passive_voice")

    def test_fts5_exam_items_virtual_table(self) -> None:
        with session_scope(self.conn) as session:
            session.execute(
                text(
                    """
                    INSERT INTO exam_items_fts (item_id, paper_id, section_code, stem_text, canonical_answer, concept_keywords)
                    VALUES (:id, :pid, :sec, :stem, :ans, :kw)
                    """
                ),
                {
                    "id": "item_1",
                    "pid": "paper_1",
                    "sec": "vocabulary",
                    "stem": "Solar panels convert sunlight into clean energy.",
                    "ans": "energy",
                    "kw": "renewable energy solar clean",
                },
            )
            session.commit()

            rows = session.execute(
                text(
                    "SELECT item_id, stem_text FROM exam_items_fts WHERE exam_items_fts MATCH 'sunlight'"
                )
            ).fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0], "item_1")


if __name__ == "__main__":
    unittest.main()
