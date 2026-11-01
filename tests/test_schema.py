import sqlite3
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from schema import init_db

class TestSchema(unittest.TestCase):
    def test_tables_created(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual table')")
        tables = {row[0] for row in cur.fetchall()}
        self.assertIn("lessons", tables)
        self.assertIn("vocabulary", tables)
        self.assertIn("passages_fts", tables)
        self.assertIn("rubrics", tables)

if __name__ == "__main__":
    unittest.main()
