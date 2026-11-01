import sqlite3
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from schema import init_db
from seed_vision1 import seed_all

class TestSeed(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        init_db(self.conn)
        seed_all(self.conn)

    def test_vision1_lessons_count(self):
        cur = self.conn.execute("SELECT COUNT(*) FROM lessons WHERE grade = 10")
        self.assertEqual(cur.fetchone()[0], 4)

    def test_vocabulary_populated(self):
        cur = self.conn.execute("SELECT COUNT(*) FROM vocabulary WHERE grade = 10 AND lesson_num = 1")
        self.assertGreaterEqual(cur.fetchone()[0], 35)
        cur_base = self.conn.execute("SELECT COUNT(*) FROM vocabulary WHERE grade < 10")
        self.assertGreaterEqual(cur_base.fetchone()[0], 250)

    def test_passages_searchable(self):
        cur = self.conn.execute("SELECT COUNT(*) FROM passages_fts WHERE passages_fts MATCH 'cheetah'")
        self.assertGreaterEqual(cur.fetchone()[0], 1)

    def test_rubrics_populated(self):
        cur = self.conn.execute("SELECT COUNT(*) FROM rubrics WHERE grade = 10")
        self.assertGreaterEqual(cur.fetchone()[0], 2)

if __name__ == "__main__":
    unittest.main()
