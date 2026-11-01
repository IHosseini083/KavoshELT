from __future__ import annotations

import os
from typing import Any, Dict, List

from sqlalchemy import func, select
from models import DbTarget, Lesson, Passage, session_scope
from validator import validate_exam_text


def run_curriculum_audit(conn: DbTarget) -> Dict[str, Any]:
    with session_scope(conn) as session:
        grades_count = int(session.scalar(select(func.count(func.distinct(Lesson.grade)))) or 0)
        lessons_count = int(session.scalar(select(func.count()).select_from(Lesson)) or 0)
        passages = list(session.scalars(select(Passage)).all())

    failures: List[Dict[str, Any]] = []
    for p in passages:
        res = validate_exam_text(conn, max_grade=p.grade, max_lesson=p.lesson_num, text=p.content)
        if not res["is_valid"]:
            failures.append(
                {
                    "grade": p.grade,
                    "lesson_num": p.lesson_num,
                    "section": f"{p.section_type}: {p.title}",
                    "out_of_syllabus_words": res["out_of_syllabus_words"],
                    "forbidden_grammar_hits": res["forbidden_grammar_hits"],
                }
            )

    passed = (len(failures) == 0) and (grades_count == 6) and (lessons_count == 31)

    return {
        "total_grades": grades_count,
        "total_lessons": lessons_count,
        "total_passages_audited": len(passages),
        "passage_validation_failures": failures,
        "audit_passed": passed,
    }


if __name__ == "__main__":
    db_path = os.path.join(os.path.dirname(__file__), "data", "curriculum.db")
    if os.path.exists(db_path):
        report = run_curriculum_audit(db_path)
        print("Audit report:", report)
