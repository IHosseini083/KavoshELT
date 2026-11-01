import glob
import json
import os
import sqlite3
from typing import Optional

from schema import init_db
from seed_vision1 import PROSPECT_BASE_LEMMAS

DEFAULT_DATASETS_DIR = os.path.join(os.path.dirname(__file__), "datasets")
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "curriculum.db")

def seed_curriculum(conn: sqlite3.Connection, datasets_dir: str = DEFAULT_DATASETS_DIR) -> None:
    cur = conn.cursor()
    
    # Clean up virtual table to prevent duplicates
    cur.execute("DELETE FROM passages_fts")
    
    # Seed baseline lemmas (Grade 6 level / general high frequency baseline)
    prospect_tuples = [
        (word, word, "base", 6, 0, "واژگان پایه مشترک", f"This is {word}.")
        for word in PROSPECT_BASE_LEMMAS
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO vocabulary (word, lemma, pos, grade, lesson_num, definition_fa, example_en) VALUES (?, ?, ?, ?, ?, ?, ?)",
        prospect_tuples
    )
    
    json_files = sorted(glob.glob(os.path.join(datasets_dir, "grade*.json")))
    for jf in json_files:
        with open(jf, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        grade = data["grade"]
        
        # 1. Lessons
        for l in data.get("lessons", []):
            cur.execute(
                "INSERT OR REPLACE INTO lessons (grade, lesson_num, title, theme, allowed_grammar, forbidden_grammar) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    grade,
                    l["lesson_num"],
                    l["title"],
                    l["theme"],
                    json.dumps(l["allowed_grammar"]),
                    json.dumps(l["forbidden_grammar"])
                )
            )
            
        # 2. Vocabulary
        for v in data.get("vocabulary", []):
            # v format: [word, lemma, pos, lesson_num, def_fa, ex_en]
            cur.execute(
                "INSERT OR IGNORE INTO vocabulary (word, lemma, pos, grade, lesson_num, definition_fa, example_en) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (v[0], v[1], v[2], grade, v[3], v[4], v[5])
            )
            
        # 3. Passages
        for p in data.get("passages", []):
            cur.execute(
                "INSERT INTO passages_fts (grade, lesson_num, section_type, title, content) VALUES (?, ?, ?, ?, ?)",
                (str(grade), p["lesson_num"], p["section_type"], p["title"], p["content"])
            )
            
        # 4. Rubrics
        for r in data.get("rubrics", []):
            cur.execute(
                "INSERT OR REPLACE INTO rubrics (id, grade, term, exam_type, total_points, structure_json) VALUES (?, ?, ?, ?, ?, ?)",
                (r["id"], grade, r["term"], r["exam_type"], r["total_points"], json.dumps(r["structure"]))
            )
            
    conn.commit()

def build_database(db_path: str = DEFAULT_DB_PATH) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    init_db(conn)
    seed_curriculum(conn)
    conn.close()
    print(f"Full 6-grade curriculum database seeded at: {db_path}")

if __name__ == "__main__":
    build_database()
