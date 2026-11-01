from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy import select

from models import (
    ConceptNode,
    DbTarget,
    ExamQuestionItem,
    NationalExamPaper,
    session_scope,
)
from validator import validate_exam_text


def verify_item(conn: DbTarget, item: ExamQuestionItem) -> dict[str, Any]:
    errors: list[str] = []

    # Rule V1: Point precision (multiple of 0.25)
    pts = float(item.points)
    if pts <= 0.0:
        errors.append(f"Points must be positive, got {pts}")
    elif abs(pts * 4.0 - round(pts * 4.0)) > 1e-4:
        errors.append(f"Points must be a precise multiple of 0.25, got {pts}")

    # Rubric breakdown precision
    rubric_dict: dict[str, Any] = {}
    if item.rubric_breakdown_json:
        try:
            rubric_dict = json.loads(item.rubric_breakdown_json)
        except Exception as e:
            errors.append(f"Invalid rubric_breakdown_json: {e}")

    if rubric_dict:
        sub_sum = sum(
            float(v) for v in rubric_dict.values() if isinstance(v, (int, float))
        )
        if abs(sub_sum - pts) > 1e-4:
            errors.append(
                f"Rubric breakdown sum ({sub_sum}) does not match item points ({pts})"
            )
    elif item.item_type in ("paragraph_writing", "open_ended"):
        errors.append(
            "Open-ended and paragraph writing items require non-empty rubric_breakdown_json"
        )

    # Rule V2: Syllabus alignment
    clean_stem = re.sub(r"^[a-d]\)\s*", "", item.stem_text, flags=re.IGNORECASE)
    clean_ans = re.sub(r"^[a-d]\)\s*", "", item.canonical_answer, flags=re.IGNORECASE)
    combined_text = f"{clean_stem} {clean_ans}"
    if item.options_json:
        try:
            opts = json.loads(item.options_json)
            if isinstance(opts, list):
                clean_opts = [
                    re.sub(r"^[a-d]\)\s*", "", str(o), flags=re.IGNORECASE)
                    for o in opts
                ]
                combined_text += " " + " ".join(clean_opts)
        except Exception:
            pass

    # Validate against Vision 3 curriculum boundary
    target_grade = max(7, min(12, int(item.grade)))
    target_lesson = max(1, min(3, int(item.lesson_num))) if target_grade == 12 else 4
    val_res = validate_exam_text(
        conn, max_grade=target_grade, max_lesson=target_lesson, text=combined_text
    )
    if not val_res["is_valid"]:
        if val_res["out_of_syllabus_words"]:
            errors.append(
                f"Stem/options contain out-of-syllabus vocabulary for Grade {target_grade} Lesson {target_lesson}: {val_res['out_of_syllabus_words']}"
            )
        if val_res["forbidden_grammar_hits"]:
            errors.append(
                f"Stem contains forbidden grammar for Grade {target_grade} Lesson {target_lesson}: {val_res['forbidden_grammar_hits']}"
            )

    # Rule V3: Concept graph integrity
    concept_ids: list[str] = []
    if item.concept_ids_json:
        try:
            c_data = json.loads(item.concept_ids_json)
            if isinstance(c_data, list):
                concept_ids = [str(c) for c in c_data]
        except Exception as e:
            errors.append(f"Invalid concept_ids_json: {e}")

    if concept_ids:
        with session_scope(conn) as session:
            existing_nodes = set(
                session.scalars(
                    select(ConceptNode.id).where(ConceptNode.id.in_(concept_ids))
                ).all()
            )
            missing = set(concept_ids) - existing_nodes
            if missing:
                errors.append(
                    f"Referenced Concept Node(s) do not exist: {sorted(missing)}"
                )
    else:
        errors.append("Item must link to at least one valid concept_id")

    # Rule V4: Answer key completeness
    if item.item_type == "multiple_choice":
        options_list: list[str] = []
        if item.options_json:
            try:
                raw_opts = json.loads(item.options_json)
                if isinstance(raw_opts, list):
                    options_list = [str(o).strip() for o in raw_opts]
            except Exception:
                pass

        if len(options_list) < 2:
            errors.append(
                "Multiple choice items must provide at least 2 options in options_json"
            )
        else:
            can_ans = str(item.canonical_answer).strip().lower()
            norm_opts = [o.lower() for o in options_list]
            # Match either full option string or leading letter or trailing text
            matched = any(
                can_ans == opt
                or can_ans in opt
                or opt.endswith(can_ans)
                or (len(can_ans) == 1 and opt.startswith(can_ans))
                for opt in norm_opts
            )
            if not matched:
                errors.append(
                    f"Canonical answer '{item.canonical_answer}' not found among options: {options_list}"
                )

    return {
        "item_id": item.id,
        "is_valid": len(errors) == 0,
        "errors": errors,
    }


def verify_paper(conn: DbTarget, paper_id: str) -> dict[str, Any]:
    with session_scope(conn) as session:
        paper = session.get(NationalExamPaper, paper_id)
        if not paper:
            return {
                "paper_id": paper_id,
                "is_valid": False,
                "errors": [f"Paper {paper_id} not found"],
            }

        items = list(
            session.scalars(
                select(ExamQuestionItem)
                .where(ExamQuestionItem.paper_id == paper_id)
                .order_by(ExamQuestionItem.id.asc())
            ).all()
        )

    item_reports = [verify_item(conn, item) for item in items]
    paper_errors: list[str] = []

    total_pts = sum(float(it.points) for it in items)
    if abs(total_pts - float(paper.total_written_points)) > 1e-4:
        paper_errors.append(
            f"Paper items total points ({total_pts}) does not match paper header total ({paper.total_written_points})"
        )

    all_items_valid = all(rep["is_valid"] for rep in item_reports)
    return {
        "paper_id": paper_id,
        "shamsi_year": paper.shamsi_year,
        "session": paper.session,
        "total_items": len(items),
        "total_points": total_pts,
        "is_valid": all_items_valid and len(paper_errors) == 0,
        "paper_errors": paper_errors,
        "item_failures": [rep for rep in item_reports if not rep["is_valid"]],
    }


def audit_national_exam_bank(conn: DbTarget) -> dict[str, Any]:
    with session_scope(conn) as session:
        papers = list(
            session.scalars(
                select(NationalExamPaper).order_by(NationalExamPaper.shamsi_year.asc())
            ).all()
        )

    paper_reports = [verify_paper(conn, p.id) for p in papers]
    total_items = sum(r.get("total_items", 0) for r in paper_reports)
    failed_papers = [r for r in paper_reports if not r["is_valid"]]

    return {
        "total_papers": len(papers),
        "total_items": total_items,
        "all_papers_valid": len(failed_papers) == 0,
        "failed_papers_count": len(failed_papers),
        "failures": failed_papers,
    }
