"""Self-consistency and coverage audit of the seeded curriculum + exam bank.

``errors``   structural invariants that must always hold (dangling keys, orphans,
             malformed JSON, broken answer keys / scoring rubrics).
``warnings`` content-coverage gaps that should be completed over time (missing
             distractor notes, lessons without conversation text, ...).
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from sqlalchemy import select

from kavosh.models import (
    ConceptEdge,
    ConceptNode,
    DbTarget,
    ExamQuestionItem,
    L1ErrorPattern,
    Lesson,
    NationalExamPaper,
    Passage,
    Vocabulary,
    session_scope,
)

EXPECTED_LESSONS: dict[int, int] = {7: 8, 8: 7, 9: 6, 10: 4, 11: 3, 12: 3}
EXPECTED_PAPERS = 27
EXPECTED_YEARS = range(1397, 1406)
BLOOM_LEVELS = frozenset(
    {"remember", "understand", "apply", "analyze", "evaluate", "create"}
)
QUARTER = 0.25
_TOL = 1e-6


def _is_quarter(value: float) -> bool:
    return value > 0 and abs(value / QUARTER - round(value / QUARTER)) < _TOL


def _parse(raw: str | None, kind: type | tuple[type, ...]) -> tuple[Any, bool]:
    """Parse optional JSON; returns ``(value, ok)`` (empty/``None`` => ok)."""
    if raw in (None, "", "None"):
        return None, True
    try:
        value = json.loads(raw) if raw is not None else None
    except ValueError:
        return None, False
    return value, isinstance(value, kind)


def run_integrity_audit(target: DbTarget) -> dict[str, Any]:
    where: dict[str, Any]
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    def err(code: str, message: str, **ctx: Any) -> None:
        errors.append({"code": code, "message": message, **ctx})

    def warn(code: str, message: str, **ctx: Any) -> None:
        warnings.append({"code": code, "message": message, **ctx})

    with session_scope(target) as session:
        lessons = list(session.scalars(select(Lesson)).all())
        vocab = list(session.scalars(select(Vocabulary)).all())
        passages = list(session.scalars(select(Passage)).all())
        nodes = {n.id: n for n in session.scalars(select(ConceptNode)).all()}
        edges = list(session.scalars(select(ConceptEdge)).all())
        l1 = list(session.scalars(select(L1ErrorPattern)).all())
        papers = {p.id: p for p in session.scalars(select(NationalExamPaper)).all()}
        items = list(session.scalars(select(ExamQuestionItem)).all())

    # ---- lessons -----------------------------------------------------------------
    per_grade = Counter(les.grade for les in lessons)
    if dict(per_grade) != EXPECTED_LESSONS:
        err(
            "lesson_count",
            f"Expected lessons per grade {EXPECTED_LESSONS}, found {dict(sorted(per_grade.items()))}",
        )
    lesson_keys = {(les.grade, les.lesson_num) for les in lessons}
    for les in lessons:
        where = {"grade": les.grade, "lesson": les.lesson_num}
        for name in ("allowed_grammar", "forbidden_grammar"):
            _, ok = _parse(getattr(les, name), (dict, list))
            if not ok:
                err("malformed_json", f"lessons.{name} is not valid JSON", **where)
        for name in (
            "grammar_details_json",
            "writing_skills_json",
            "vocab_development_json",
            "see_also_json",
        ):
            raw = getattr(les, name)
            if raw is None:
                warn("missing_lesson_section", f"lessons.{name} is empty", **where)
            else:
                _, ok = _parse(raw, (dict, list))
                if not ok:
                    err("malformed_json", f"lessons.{name} is not valid JSON", **where)

    # ---- vocabulary / passages ---------------------------------------------------
    vocab_by_lesson: dict[tuple[int, int], set[str]] = {}
    for v in vocab:
        if v.grade < 7:  # shared grade-6 word bank
            continue
        if (v.grade, v.lesson_num) not in lesson_keys:
            err(
                "orphan_vocabulary",
                f"Vocabulary {v.lemma!r} references missing lesson",
                grade=v.grade,
                lesson=v.lesson_num,
            )
        if not v.lemma.strip() or not v.word.strip():
            err("empty_vocabulary", f"Vocabulary row {v.id} has an empty word/lemma")
        vocab_by_lesson.setdefault((v.grade, v.lesson_num), set()).add(
            v.section_source or "vocabulary"
        )
    passage_kinds: dict[tuple[int, int], set[str]] = {}
    for p in passages:
        if (p.grade, p.lesson_num) not in lesson_keys:
            err(
                "orphan_passage",
                f"Passage {p.title!r} references missing lesson",
                grade=p.grade,
                lesson=p.lesson_num,
            )
        if not p.content.strip():
            err("empty_passage", f"Passage {p.title!r} has no text")
        passage_kinds.setdefault((p.grade, p.lesson_num), set()).add(
            p.section_type.lower()
        )
    for key in sorted(lesson_keys):
        where = {"grade": key[0], "lesson": key[1]}
        if key not in vocab_by_lesson:
            warn("lesson_without_vocabulary", "Lesson has no vocabulary", **where)
        kinds = passage_kinds.get(key, set())
        for needed in ("conversation", "reading"):
            if needed not in kinds:
                warn("lesson_missing_passage", f"No {needed} passage", **where)
        if "listening" not in kinds:
            warn("lesson_missing_passage", "No listening script", **where)

    # ---- concept graph -----------------------------------------------------------
    for e in edges:
        if e.source_id not in nodes:
            err("dangling_edge", f"Edge {e.id} source {e.source_id!r} missing")
        if e.target_id not in nodes:
            warn(
                "external_edge_target",
                f"Edge {e.id} target {e.target_id!r} is not a seeded node (lower-grade ref)",
            )
    for pat in l1:
        if pat.concept_id not in nodes:
            err("dangling_l1_pattern", f"L1 pattern {pat.id} concept missing")

    # ---- exam bank ---------------------------------------------------------------
    if len(papers) != EXPECTED_PAPERS:
        warn("paper_count", f"Expected {EXPECTED_PAPERS} papers, found {len(papers)}")
    missing_years = set(EXPECTED_YEARS) - {p.shamsi_year for p in papers.values()}
    if missing_years:
        warn("paper_years", f"Missing exam years: {sorted(missing_years)}")

    totals: dict[str, float] = {}
    for it in items:
        where = {"item": it.id}
        paper = papers.get(it.paper_id)
        if paper is None:
            err("dangling_item_paper", f"Item {it.id} references missing paper")
        totals[it.paper_id] = totals.get(it.paper_id, 0.0) + float(it.points)

        if not it.canonical_answer.strip():
            err("missing_answer_key", "Item has an empty canonical answer", **where)
        if not _is_quarter(float(it.points)):
            err(
                "points_granularity", f"Points {it.points} not a 0.25 multiple", **where
            )

        options, ok = _parse(it.options_json, list)
        if not ok:
            err("malformed_json", "options_json is not a JSON list", **where)
        elif it.item_type == "multiple_choice" and (not options or len(options) < 2):
            err("missing_options", "Multiple-choice item lacks options", **where)
        rubric, ok = _parse(it.rubric_breakdown_json, dict)
        if not ok:
            err("malformed_json", "rubric_breakdown_json is not a JSON object", **where)
        elif rubric:
            if any(not _is_quarter(float(x)) for x in rubric.values()):
                err("rubric_granularity", "Rubric part not a 0.25 multiple", **where)
            if abs(sum(float(x) for x in rubric.values()) - float(it.points)) > _TOL:
                err("rubric_sum", "Rubric parts do not sum to item points", **where)
        else:
            warn("missing_rubric", "Item has no rubric breakdown", **where)
        for name in ("acceptable_variants_json", "concept_ids_json"):
            _, ok = _parse(getattr(it, name), list)
            if not ok:
                err("malformed_json", f"{name} is not a JSON list", **where)
        concept_ids, _ = _parse(it.concept_ids_json, list)
        for cid in concept_ids or []:
            if cid not in nodes:
                err(
                    "dangling_concept",
                    f"Item references unknown concept {cid!r}",
                    **where,
                )
        if it.bloom_level not in BLOOM_LEVELS:
            warn("bloom_tag", f"Unknown Bloom level {it.bloom_level!r}", **where)
        if (
            it.item_type == "multiple_choice"
            and not (it.distractor_analysis or "").strip()
        ):
            warn(
                "missing_distractor_notes", "MCQ lacks distractor diagnostics", **where
            )

    for pid, paper in papers.items():
        if (
            pid in totals
            and abs(totals[pid] - float(paper.total_written_points)) > _TOL
        ):
            err(
                "paper_total",
                f"Paper {pid} items sum to {totals[pid]}, header says {paper.total_written_points}",
            )
        if pid not in totals:
            warn("empty_paper", f"Paper {pid} has no items")

    summary = Counter(w["code"] for w in warnings)
    return {
        "passed": not errors,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "warning_summary": dict(sorted(summary.items())),
        "counts": {
            "lessons": len(lessons),
            "vocabulary": len(vocab),
            "passages": len(passages),
            "concept_nodes": len(nodes),
            "concept_edges": len(edges),
            "l1_patterns": len(l1),
            "exam_papers": len(papers),
            "exam_items": len(items),
        },
    }
