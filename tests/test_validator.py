from __future__ import annotations

import sqlite3
import unittest

from kavosh.schema import init_db
from kavosh.seeder import seed_curriculum
from kavosh.validator import validate_exam_text


class TestValidator(unittest.TestCase):
    conn: sqlite3.Connection

    @classmethod
    def setUpClass(cls) -> None:
        cls.conn = sqlite3.connect(":memory:")
        init_db(cls.conn)
        seed_curriculum(cls.conn)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.conn.close()

    def test_valid_lesson1_sentence_passes(self) -> None:
        text = "Humans will protect the endangered Iranian cheetah in nature."
        res = validate_exam_text(self.conn, max_grade=10, max_lesson=1, text=text)
        self.assertEqual(res["out_of_syllabus_words"], [])
        self.assertEqual(res["forbidden_grammar_hits"], [])
        self.assertTrue(res["is_valid"])

    def test_out_of_syllabus_word_detected(self) -> None:
        text = "The photosynthesis phenomenon requires chlorophyll."
        res = validate_exam_text(self.conn, max_grade=10, max_lesson=1, text=text)
        self.assertIn("photosynthesis", res["out_of_syllabus_words"])
        self.assertIn("chlorophyll", res["out_of_syllabus_words"])
        self.assertFalse(res["is_valid"])

    def test_forbidden_grammar_present_perfect_detected(self) -> None:
        text = "Amir has visited the forest many times."
        res = validate_exam_text(self.conn, max_grade=10, max_lesson=2, text=text)
        self.assertGreater(len(res["forbidden_grammar_hits"]), 0)
        self.assertFalse(res["is_valid"])

    def test_past_progressive_forbidden_in_lesson1_allowed_in_lesson3(self) -> None:
        text = "Ali was watching the wild animals in the forest."
        res_l1 = validate_exam_text(self.conn, max_grade=10, max_lesson=1, text=text)
        self.assertGreater(len(res_l1["forbidden_grammar_hits"]), 0)
        res_l3 = validate_exam_text(self.conn, max_grade=10, max_lesson=3, text=text)
        self.assertEqual(res_l3["forbidden_grammar_hits"], [])

    def test_inflections_recognized(self) -> None:
        text = "The heart is pumping blood faster to protect the body."
        res = validate_exam_text(self.conn, max_grade=10, max_lesson=2, text=text)
        self.assertEqual(res["out_of_syllabus_words"], [])
        self.assertTrue(res["is_valid"])


if __name__ == "__main__":
    unittest.main()
