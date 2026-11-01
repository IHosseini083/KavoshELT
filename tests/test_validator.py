import sqlite3
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from schema import init_db
from seed_vision1 import seed_all
from validator import validate_exam_text

class TestValidator(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        init_db(self.conn)
        seed_all(self.conn)

    def test_valid_lesson1_sentence_passes(self):
        text = "Humans will protect the endangered Iranian cheetah in nature."
        res = validate_exam_text(self.conn, max_grade=10, max_lesson=1, text=text)
        self.assertEqual(res["out_of_syllabus_words"], [])
        self.assertEqual(res["forbidden_grammar_hits"], [])
        self.assertTrue(res["is_valid"])

    def test_out_of_syllabus_word_detected(self):
        text = "The photosynthesis phenomenon requires chlorophyll."
        res = validate_exam_text(self.conn, max_grade=10, max_lesson=1, text=text)
        self.assertIn("photosynthesis", res["out_of_syllabus_words"])
        self.assertIn("chlorophyll", res["out_of_syllabus_words"])
        self.assertFalse(res["is_valid"])

    def test_forbidden_grammar_present_perfect_detected(self):
        text = "Amir has visited the forest many times."
        res = validate_exam_text(self.conn, max_grade=10, max_lesson=2, text=text)
        self.assertTrue(len(res["forbidden_grammar_hits"]) > 0)
        self.assertFalse(res["is_valid"])

    def test_past_progressive_forbidden_in_lesson1_allowed_in_lesson3(self):
        text = "Ali was watching the wild animals in the forest."
        # In lesson 1, past progressive is not taught yet
        res_l1 = validate_exam_text(self.conn, max_grade=10, max_lesson=1, text=text)
        self.assertTrue(len(res_l1["forbidden_grammar_hits"]) > 0)
        # In lesson 3, past progressive is officially part of syllabus
        res_l3 = validate_exam_text(self.conn, max_grade=10, max_lesson=3, text=text)
        self.assertEqual(res_l3["forbidden_grammar_hits"], [])

    def test_inflections_recognized(self):
        # "trees" (tree+s), "pumping" (pump+ing), "protected" (protect+ed), "faster" (fast+er)
        text = "The heart is pumping blood faster to protect the body."
        res = validate_exam_text(self.conn, max_grade=10, max_lesson=2, text=text)
        self.assertEqual(res["out_of_syllabus_words"], [])

if __name__ == "__main__":
    unittest.main()
