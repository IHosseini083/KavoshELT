from __future__ import annotations

import json
import os
import uuid
from typing import Any

from kavosh.exam_rag import retrieve_exam_items, synthesize_twin_item
from kavosh.knapsack import select_items_for_target_points
from kavosh.models import DbTarget
from kavosh.styler import (
    generate_answer_key_pdf,
    generate_exam_docx,
    generate_exam_html,
    generate_exam_pdf,
)

OFFICIAL_SECTION_TITLES_FA: dict[str, str] = {
    "vocabulary": "بخش واژگان (Vocabulary)",
    "grammar": "بخش دستور زبان (Grammar)",
    "writing": "بخش نگارش و بندنویسی (Writing)",
    "cloze": "آزمون کلوزتست (Cloze Test)",
    "reading": "درک مطلب ریدینگ (Reading Comprehension)",
    "pronunciation": "تلفظ و آهنگ کلام (Pronunciation)",
}


_select_items_for_target_points = select_items_for_target_points


def default_exports_dir() -> str:
    """Output root for composed exams: ``$KAVOSH_EXPORTS_DIR`` or ``./exports/composed``.

    Resolved against the current directory at call time so an installed wheel never
    writes into ``site-packages``.
    """
    return os.environ.get("KAVOSH_EXPORTS_DIR") or os.path.join(
        os.getcwd(), "exports", "composed"
    )


def _apply_sourcing(
    conn: DbTarget,
    items: list[dict[str, Any]],
    sourcing: str,
) -> list[dict[str, Any]]:
    processed: list[dict[str, Any]] = []
    for idx, it in enumerate(items):
        if sourcing == "ai_twins" or (sourcing == "hybrid" and idx % 2 == 1):
            twin = synthesize_twin_item(conn, it["id"], variation_index=idx)
            if twin and twin["is_valid"]:
                twin["shamsi_year"] = it.get("shamsi_year", 1403)
                twin["session"] = it.get("session", "Khordad")
                processed.append(twin)
            else:
                processed.append(it)
        else:
            processed.append(it)
    return processed


def _render_composed_markdown(
    title: str,
    grade: int,
    school_name: str,
    teacher_name: str,
    total_points: float,
    sections: list[dict[str, Any]],
) -> str:
    series = "Prospect" if grade <= 9 else "Vision"
    grade_fa = {
        7: "هفتم",
        8: "هشتم",
        9: "نهم",
        10: "دهم",
        11: "یازدهم",
        12: "دوازدهم",
    }.get(grade, str(grade))

    lines: list[str] = [
        f"# {title} - پایه {grade_fa} ({series})",
        "",
        f"**مشخصات آزمون:** آموزشگاه: {school_name} | طراح: {teacher_name} | بارم کل کتبی: {total_points:.2f} نمره",
        "---",
        "",
        "## بخش اول: برگه سوالات دانش‌آموز (Student's Question Sheet)",
        "",
    ]

    q_counter = 1
    answer_key_lines: list[str] = []

    for sec in sections:
        sec_code = sec["section_code"]
        sec_title = OFFICIAL_SECTION_TITLES_FA.get(sec_code, sec_code.title())
        lines.append(f"### {sec_title} — [{sec['section_points']:.2f} Points]")
        answer_key_lines.append(
            f"### {sec_title} (بارم بخش: {sec['section_points']:.2f} نمره)"
        )

        for it in sec["items"]:
            it["display_num"] = q_counter
            pts = float(it["points"])
            prov = (
                "هم‌تراز نو"
                if it.get("is_synthetic_twin")
                else f"{it.get('session', '')} {it.get('shamsi_year', '')}"
            )
            badge_text = f"[{prov} — {pts:.2f} نمره]"

            if it.get("passage_text"):
                lines.append(f"> **Passage:** {it['passage_text']}")
                lines.append("")

            lines.append(f"**{q_counter}. {it['stem_text']}** {badge_text}")

            if it.get("options_json"):
                try:
                    opts = json.loads(it["options_json"])
                    if isinstance(opts, list):
                        for opt in opts:
                            lines.append(f"- {opt}")
                except (ValueError, TypeError):
                    pass

            lines.append("")

            rubric_str = ""
            if it.get("rubric_breakdown_json"):
                try:
                    r_dict = json.loads(it["rubric_breakdown_json"])
                    if isinstance(r_dict, dict):
                        r_parts = [f"{k}: {v:.2f}" for k, v in r_dict.items()]
                        rubric_str = f" [ریزبارم: {', '.join(r_parts)}]"
                except (ValueError, TypeError):
                    pass

            answer_key_lines.append(
                f"{q_counter}. **{it['canonical_answer']}** ({pts:.2f} نمره){rubric_str}"
            )
            q_counter += 1

        lines.append("---")
        lines.append("")

    lines.append("## بخش دوم: کلید سوالات و راهنمای تصحیح رسمی (Official Scoring Key)")
    lines.extend(answer_key_lines)

    return "\n".join(lines) + "\n"


def compose_exam(
    conn: DbTarget,
    mode: str = "full_mock",
    grade: int = 12,
    lessons: list[int] | None = None,
    section: str | None = None,
    target_points: float = 28.0,
    sourcing: str = "past_papers",
    school_name: str = "دبیرستان نمونه دولتی",
    teacher_name: str = "دبیر محترم",
    year_min: int | None = None,
    year_max: int | None = None,
    sessions: list[str] | None = None,
    out_dir: str | None = None,
) -> dict[str, Any]:
    comp_id = uuid.uuid4().hex[:10]
    target_out_dir = out_dir or os.path.join(default_exports_dir(), comp_id)
    os.makedirs(target_out_dir, exist_ok=True)

    composed_sections: list[dict[str, Any]] = []

    if mode == "full_mock":
        blueprint_slots: list[tuple[str, float]] = [
            ("vocabulary", 6.0),
            ("grammar", 5.0),
            ("writing", 6.0),
            ("cloze", 3.0),
            ("reading", 8.0),
        ]
        scale = target_points / 28.0

        for sec_code, base_pts in blueprint_slots:
            slot_target = round(base_pts * scale, 2)
            pool = retrieve_exam_items(
                conn,
                grade=grade,
                lessons=lessons,
                sections=[sec_code],
                sessions=sessions,
                year_min=year_min,
                year_max=year_max,
                top_k=25,
            )
            selected, curr_pts = _select_items_for_target_points(pool, slot_target)
            processed_items = _apply_sourcing(conn, selected, sourcing)
            composed_sections.append(
                {
                    "section_code": sec_code,
                    "section_points": curr_pts,
                    "items": processed_items,
                }
            )

    elif mode == "skill_worksheet":
        target_sec = section or "writing"
        pool = retrieve_exam_items(
            conn,
            grade=grade,
            lessons=lessons,
            sections=[target_sec],
            sessions=sessions,
            year_min=year_min,
            year_max=year_max,
            top_k=30,
        )
        selected, curr_pts = _select_items_for_target_points(pool, target_points)
        processed_items = _apply_sourcing(conn, selected, sourcing)
        composed_sections.append(
            {
                "section_code": target_sec,
                "section_points": curr_pts,
                "items": processed_items,
            }
        )

    else:  # custom_quiz
        target_lessons = lessons or [1]
        active_sections = ["vocabulary", "grammar", "writing"]
        composed_sections = [
            {"section_code": sec, "section_points": 0.0, "items": []}
            for sec in active_sections
        ]

        candidates_by_sec = {
            sec: retrieve_exam_items(
                conn,
                grade=grade,
                lessons=target_lessons,
                sections=[sec],
                sessions=sessions,
                year_min=year_min,
                year_max=year_max,
                top_k=20,
            )
            for sec in active_sections
        }

        curr_total = 0.0
        while curr_total < target_points - 1e-4:
            made_progress = False
            for sec_dict in composed_sections:
                sec_code = sec_dict["section_code"]
                for it in candidates_by_sec[sec_code]:
                    if (
                        it not in sec_dict["items"]
                        and curr_total + it["points"] <= target_points + 1e-4
                    ):
                        sec_dict["items"].append(it)
                        sec_dict["section_points"] = round(
                            sec_dict["section_points"] + it["points"], 2
                        )
                        curr_total = round(curr_total + it["points"], 2)
                        made_progress = True
                        break
            if not made_progress:
                break

        for sec_dict in composed_sections:
            sec_dict["items"] = _apply_sourcing(conn, sec_dict["items"], sourcing)

    actual_total_pts = sum(sec["section_points"] for sec in composed_sections)

    exam_title = f"آزمون استاندارد نهایی کشوری ({mode})"
    if mode == "skill_worksheet":
        exam_title = f"کاربرگ تخصصی مهارت {OFFICIAL_SECTION_TITLES_FA.get(section or 'writing', '')}"
    elif mode == "custom_quiz":
        exam_title = f"کوئیز کلاسی درس {', '.join(str(x) for x in (lessons or [1]))}"

    md_content = _render_composed_markdown(
        title=exam_title,
        grade=grade,
        school_name=school_name,
        teacher_name=teacher_name,
        total_points=actual_total_pts,
        sections=composed_sections,
    )

    md_path = os.path.join(target_out_dir, "exam.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    student_pdf = os.path.join(target_out_dir, "student_sheet.pdf")
    student_docx = os.path.join(target_out_dir, "student_sheet.docx")
    student_html = os.path.join(target_out_dir, "student_sheet.html")
    answer_key_pdf = os.path.join(target_out_dir, "teacher_answer_key.pdf")

    generate_exam_pdf(md_path, student_pdf, school_name=school_name)
    generate_exam_docx(md_path, student_docx, school_name=school_name)
    generate_exam_html(md_path, student_html, school_name=school_name)
    generate_answer_key_pdf(md_path, answer_key_pdf, school_name=school_name)

    return {
        "composition_id": comp_id,
        "mode": mode,
        "sourcing": sourcing,
        "grade": grade,
        "lessons": lessons,
        "total_points": actual_total_pts,
        "school_name": school_name,
        "teacher_name": teacher_name,
        "sections": composed_sections,
        "markdown_path": md_path,
        "student_pdf": student_pdf,
        "student_docx": student_docx,
        "student_html": student_html,
        "answer_key_pdf": answer_key_pdf,
    }


def swap_slot_item(
    conn: DbTarget,
    composed_exam: dict[str, Any],
    slot_id: str,
) -> dict[str, Any]:
    target_sec = None
    target_item = None
    target_idx = -1

    existing_ids: set[str] = set()
    for sec in composed_exam["sections"]:
        for i, it in enumerate(sec["items"]):
            existing_ids.add(it["id"])
            if it["id"] == slot_id:
                target_sec = sec
                target_item = it
                target_idx = i

    if not target_sec or not target_item:
        return composed_exam

    candidates = retrieve_exam_items(
        conn,
        grade=target_item["grade"],
        lessons=[target_item["lesson_num"]],
        sections=[target_item["section_code"]],
        top_k=20,
    )

    new_item = None
    for cand in candidates:
        if (
            cand["id"] not in existing_ids
            and abs(cand["points"] - target_item["points"]) < 1e-4
        ):
            new_item = cand
            break

    if not new_item:
        twin = synthesize_twin_item(conn, target_item["id"], variation_index=2)
        if twin and twin["is_valid"]:
            new_item = twin
        else:
            return composed_exam

    target_sec["items"][target_idx] = new_item
    actual_total_pts = sum(sec["section_points"] for sec in composed_exam["sections"])

    md_content = _render_composed_markdown(
        title=f"آزمون استاندارد نهایی کشوری ({composed_exam['mode']})",
        grade=composed_exam["grade"],
        school_name=composed_exam["school_name"],
        teacher_name=composed_exam["teacher_name"],
        total_points=actual_total_pts,
        sections=composed_exam["sections"],
    )

    with open(composed_exam["markdown_path"], "w", encoding="utf-8") as f:
        f.write(md_content)

    generate_exam_pdf(
        composed_exam["markdown_path"],
        composed_exam["student_pdf"],
        school_name=composed_exam["school_name"],
    )
    generate_exam_docx(
        composed_exam["markdown_path"],
        composed_exam["student_docx"],
        school_name=composed_exam["school_name"],
    )
    generate_exam_html(
        composed_exam["markdown_path"],
        composed_exam["student_html"],
        school_name=composed_exam["school_name"],
    )
    generate_answer_key_pdf(
        composed_exam["markdown_path"],
        composed_exam["answer_key_pdf"],
        school_name=composed_exam["school_name"],
    )

    composed_exam["total_points"] = actual_total_pts
    return composed_exam
