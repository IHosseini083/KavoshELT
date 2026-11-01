from __future__ import annotations

import sqlite3
import unittest

from exam_rag_engine import (
    retrieve_exam_items,
    synthesize_twin_item,
    traverse_prerequisites,
)
from schema import init_db
from seed_all_grades import seed_curriculum


class TestExamRagEngine(unittest.TestCase):
    conn: sqlite3.Connection

    @classmethod
    def setUpClass(cls) -> None:
        cls.conn = sqlite3.connect(":memory:")
        init_db(cls.conn)
        seed_curriculum(cls.conn)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.conn.close()

    def test_retrieve_exam_items_filtering(self) -> None:
        items = retrieve_exam_items(
            self.conn,
            grade=12,
            lessons=[1, 2],
            sections=["grammar"],
            sessions=["Khordad"],
            year_min=1400,
            year_max=1405,
            top_k=5,
        )
        self.assertGreaterEqual(len(items), 1)
        for it in items:
            self.assertEqual(it["grade"], 12)
            self.assertIn(it["lesson_num"], [1, 2])
            self.assertEqual(it["section_code"], "grammar")
            self.assertEqual(it["session"], "Khordad")
            self.assertGreaterEqual(it["shamsi_year"], 1400)
            self.assertLessEqual(it["shamsi_year"], 1405)

    def test_retrieve_exam_items_with_semantic_query(self) -> None:
        items = retrieve_exam_items(
            self.conn,
            grade=12,
            query="solar panels and clean electricity",
            top_k=3,
        )
        self.assertGreaterEqual(len(items), 1)
        top_item = items[0]
        # Should rank renewable energy items high
        self.assertEqual(top_item["lesson_num"], 3)
        self.assertGreater(top_item["hybrid_score"], 0.0)

    def test_traverse_prerequisites(self) -> None:
        res = traverse_prerequisites(self.conn, "g12.l1.grammar.passive_voice")
        self.assertIsNotNone(res["concept"])
        self.assertEqual(res["concept"]["id"], "g12.l1.grammar.passive_voice")

        prereqs = res["prerequisites"]
        self.assertGreaterEqual(len(prereqs), 1)
        prereq_ids = [p["id"] for p in prereqs]
        self.assertIn("g9.l5.grammar.simple_past", prereq_ids)

        l1_errors = res["l1_errors"]
        self.assertGreaterEqual(len(l1_errors), 1)
        self.assertTrue(any("to be" in e["error_title_fa"] for e in l1_errors))

    def test_synthesize_twin_item_closed_loop(self) -> None:
        # Retrieve a real base grammar item
        items = retrieve_exam_items(self.conn, grade=12, sections=["grammar"], top_k=1)
        self.assertGreaterEqual(len(items), 1)
        base_item_id = items[0]["id"]

        twin = synthesize_twin_item(self.conn, base_item_id)
        self.assertIsNotNone(twin)
        assert twin is not None
        self.assertTrue(twin["is_synthetic_twin"])
        self.assertEqual(twin["parent_item_id"], base_item_id)
        self.assertEqual(twin["points"], items[0]["points"])
        self.assertTrue(
            twin["is_valid"], f"Twin errors: {twin.get('validation_errors')}"
        )


if __name__ == "__main__":
    unittest.main()
