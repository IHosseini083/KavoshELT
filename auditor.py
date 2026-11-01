import sqlite3
from typing import Dict, Any, List
from validator import validate_exam_text

def run_curriculum_audit(conn: sqlite3.Connection) -> Dict[str, Any]:
    cur = conn.cursor()
    
    # 1. Count grades and lessons
    cur.execute("SELECT COUNT(DISTINCT grade), COUNT(*) FROM lessons")
    grades_count, lessons_count = cur.fetchone()
    
    # 2. Audit all passages against their respective grade & lesson
    cur.execute("SELECT grade, lesson_num, section_type, title, content FROM passages_fts")
    passages = cur.fetchall()
    
    failures = []
    for g, l, sec_type, title, content in passages:
        grade = int(g)
        lesson_num = int(l)
        res = validate_exam_text(conn, max_grade=grade, max_lesson=lesson_num, text=content)
        if not res["is_valid"]:
            failures.append({
                "grade": grade,
                "lesson_num": lesson_num,
                "section": f"{sec_type}: {title}",
                "out_of_syllabus_words": res["out_of_syllabus_words"],
                "forbidden_grammar_hits": res["forbidden_grammar_hits"]
            })
            
    passed = (len(failures) == 0) and (grades_count == 6) and (lessons_count == 31)
    
    return {
        "total_grades": grades_count,
        "total_lessons": lessons_count,
        "total_passages_audited": len(passages),
        "passage_validation_failures": failures,
        "audit_passed": passed
    }

if __name__ == "__main__":
    import os
    db_path = os.path.join(os.path.dirname(__file__), "data", "curriculum.db")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        report = run_curriculum_audit(conn)
        print("Audit report:", report)
        conn.close()
