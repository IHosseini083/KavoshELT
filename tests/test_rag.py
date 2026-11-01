from __future__ import annotations

import sqlite3
import unittest

from rag import (
    compute_embedding,
    cosine_similarity,
    hybrid_search_passages,
    hybrid_search_vocabulary,
    retrieve_rag_context,
)
from schema import init_db
from seed_all_grades import seed_curriculum


class TestRagEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.conn = sqlite3.connect(":memory:")
        init_db(cls.conn)
        seed_curriculum(cls.conn)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.conn.close()

    def test_compute_embedding(self) -> None:
        vec = compute_embedding("cheetah and endangered wildlife")
        self.assertEqual(len(vec), 64)
        sim = cosine_similarity(vec, vec)
        self.assertAlmostEqual(sim, 1.0, places=4)

    def test_hybrid_search_passages(self) -> None:
        results = hybrid_search_passages(
            self.conn,
            query="heart and blood cells",
            max_grade=10,
            max_lesson=2,
            top_k=2,
        )
        self.assertTrue(len(results) > 0)
        self.assertIn("Heart", results[0]["title"])

    def test_hybrid_search_vocabulary(self) -> None:
        results = hybrid_search_vocabulary(
            self.conn,
            query="doctor medicine physician",
            max_grade=10,
            max_lesson=4,
            top_k=5,
        )
        self.assertTrue(len(results) > 0)
        words = [r["word"].lower() for r in results]
        self.assertTrue(
            any(w in words for w in ["physician", "medicine", "cure", "patient"])
        )

    def test_retrieve_rag_context_bounds(self) -> None:
        rag_data = retrieve_rag_context(
            self.conn, query="endangered animals", max_grade=7, max_lesson=4
        )
        self.assertEqual(rag_data["syllabus_boundary"]["max_grade"], 7)
        self.assertEqual(rag_data["syllabus_boundary"]["max_lesson"], 4)
        self.assertIn("SYLLABUS BOUNDARY", rag_data["prompt_context"])


if __name__ == "__main__":
    unittest.main()
