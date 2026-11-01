import sqlite3
from typing import Dict, Any, List
from validator import validate_exam_text, get_allowed_vocabulary

CURATED_SYNONYMS = {
    "physician": ["doctor"],
    "dentist": ["doctor"],
    "automobile": ["car"],
    "plane": ["airplane", "flight"],
    "destination": ["city", "place", "country"],
    "vacation": ["trip", "holiday", "weekend"],
    "illness": ["cold", "problem", "fever"],
    "disease": ["illness", "problem", "cold"],
    "huge": ["big", "great"],
    "tiny": ["small", "little"],
    "wealthy": ["rich"],
    "quick": ["fast"],
    "start": ["begin"],
    "finish": ["end"],
    "look for": ["search", "find"],
    "glad": ["happy"],
    "angry": ["mad"],
    "difficult": ["hard"],
    "easy": ["simple"],
    "smart": ["clever"],
    "intelligent": ["clever"],
    "tidy": ["neat", "clean"],
    "untidy": ["messy"],
    "brave": ["strong"],
    "polite": ["kind"],
    "gift": ["present"],
    "meal": ["food", "dinner", "lunch"],
    "beverage": ["drink", "tea", "water"],
    "dwelling": ["house", "home"]
}

def analyze_and_advise(conn: sqlite3.Connection, max_grade: int, max_lesson: int, text: str) -> Dict[str, Any]:
    validation = validate_exam_text(conn, max_grade, max_lesson, text)
    allowed_vocab = get_allowed_vocabulary(conn, max_grade, max_lesson)
    
    cur = conn.cursor()
    word_diagnostics = {}
    
    for word in validation["out_of_syllabus_words"]:
        w = word.lower()
        # 1. Check if word is taught in a higher grade
        cur.execute(
            "SELECT grade, lesson_num, definition_fa, pos FROM vocabulary WHERE LOWER(lemma) = ? OR LOWER(word) = ? ORDER BY grade ASC, lesson_num ASC LIMIT 1",
            (w, w)
        )
        row = cur.fetchone()
        
        taught_grade = row[0] if row else None
        taught_lesson = row[1] if row else None
        def_fa = row[2] if row else None
        
        # 2. Find in-syllabus alternatives
        alternatives = []
        if w in CURATED_SYNONYMS:
            for syn in CURATED_SYNONYMS[w]:
                if syn.lower() in allowed_vocab:
                    alternatives.append(syn)
                    
        # If no curated synonym found, check if definition keywords match
        if not alternatives and def_fa:
            cur.execute(
                """SELECT DISTINCT word FROM vocabulary 
                   WHERE definition_fa LIKE ? AND ((grade < ?) OR (grade = ? AND lesson_num <= ?))
                   LIMIT 3""",
                (f"%{def_fa}%", max_grade, max_grade, max_lesson)
            )
            for r in cur.fetchall():
                if r[0].lower() != w:
                    alternatives.append(r[0])
                    
        word_diagnostics[word] = {
            "taught_in_grade": taught_grade,
            "taught_in_lesson": taught_lesson,
            "definition_fa": def_fa,
            "in_syllabus_alternatives": alternatives
        }
        
    validation["word_diagnostics"] = word_diagnostics
    return validation
