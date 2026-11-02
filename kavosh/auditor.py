from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from kavosh.models import DbTarget, Lesson, Passage, session_scope
from kavosh.validator import validate_exam_text


def run_curriculum_audit(conn: DbTarget) -> dict[str, Any]:
    with session_scope(conn) as session:
        grades_count = int(
            session.scalar(select(func.count(func.distinct(Lesson.grade)))) or 0
        )
        lessons_count = int(
            session.scalar(select(func.count()).select_from(Lesson)) or 0
        )
        passages = list(session.scalars(select(Passage)).all())

    failures: list[dict[str, Any]] = []
    for p in passages:
        res = validate_exam_text(
            conn, max_grade=p.grade, max_lesson=p.lesson_num, text=p.content
        )
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
