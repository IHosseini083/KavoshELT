"""Transport-agnostic service layer behind the MCP tools and resources."""

from __future__ import annotations

import json
import os
import threading
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.engine import Engine

from kavosh.advisor import advise_words
from kavosh.exam_rag import retrieve_exam_items
from kavosh.models import (
    ConceptNode,
    L1ErrorPattern,
    Lesson,
    Passage,
    Vocabulary,
    create_engine_for_target,
    session_scope,
)
from kavosh.paths import resolve_db_path
from kavosh.rag import hybrid_search_passages
from kavosh.syllabus import Bound, SyllabusIndex
from kavosh.validator import validate_with_index

GRADES = range(7, 13)
MAX_LIMIT = 50


def series_name(grade: int) -> str:
    return f"Prospect {grade - 6}" if grade <= 9 else f"Vision {grade - 9}"


def _loads(raw: str | None, default: Any = None) -> Any:
    if raw in (None, "", "None"):
        return default
    try:
        return json.loads(raw) if raw is not None else default
    except ValueError:
        return default


def _clamp_limit(limit: int) -> int:
    return max(1, min(int(limit), MAX_LIMIT))


class KavoshService:
    """Holds one SQLAlchemy engine and one in-memory syllabus index."""

    def __init__(self, db_path: str | os.PathLike[str] | None = None) -> None:
        self.db_path = resolve_db_path(db_path)
        self.engine: Engine = create_engine_for_target(str(self.db_path))
        self.index = SyllabusIndex.from_target(self.engine)

    # ------------------------------------------------------------------ helpers --
    @staticmethod
    def _check_grade(grade: int) -> None:
        if grade not in GRADES:
            raise ValueError(f"grade must be between 7 and 12, got {grade}")

    def _bound(self, grade: int, lesson: int | None) -> Bound:
        self._check_grade(grade)
        last = self.index.last_lesson(grade)
        if lesson is None:
            return (grade, last)
        if not 1 <= lesson <= last:
            raise ValueError(f"Grade {grade} has lessons 1-{last}, got lesson {lesson}")
        return (grade, lesson)

    # -------------------------------------------------------------------- tools --
    def validate_text(
        self, text: str, target_grade: int, target_lesson: int | None = None
    ) -> dict[str, Any]:
        bound = self._bound(target_grade, target_lesson)
        result = validate_with_index(self.index, bound[0], bound[1], text)
        violations = [
            f"{hit['type']}: '{hit['match']}' - {hit['reason']}"
            for hit in result["forbidden_grammar_hits"]
        ]
        return {
            "is_valid": result["is_valid"],
            "out_of_bounds_tokens": result["out_of_syllabus_words"],
            "violations": violations,
            "target": {"grade": bound[0], "lesson": bound[1]},
            "word_count": result["word_count"],
        }

    def suggest_synonyms(self, text: str, target_grade: int) -> dict[str, Any]:
        bound = self._bound(target_grade, None)
        result = validate_with_index(self.index, bound[0], bound[1], text)
        flagged: list[str] = result["out_of_syllabus_words"]
        diagnostics = advise_words(self.index, flagged, bound)
        suggestions = {
            word: diag["ranked_alternatives"] for word, diag in diagnostics.items()
        }
        return {
            "target_grade": target_grade,
            "out_of_bounds_tokens": flagged,
            "suggestions": suggestions,
            "taught_in": {
                word: {
                    "grade": diag["taught_in_grade"],
                    "lesson": diag["taught_in_lesson"],
                }
                for word, diag in diagnostics.items()
            },
            "unresolved": [w for w in flagged if not suggestions[w]],
        }

    def get_lesson_bounds(self, grade: int, lesson: int) -> dict[str, Any]:
        self._bound(grade, lesson)
        with session_scope(self.engine) as session:
            les = session.get(Lesson, (grade, lesson))
            if les is None:
                raise ValueError(f"No lesson {lesson} in grade {grade}")
            vocab = session.scalars(
                select(Vocabulary)
                .where(Vocabulary.grade == grade, Vocabulary.lesson_num == lesson)
                .order_by(Vocabulary.section_source, Vocabulary.word)
            ).all()
            details = _loads(les.grammar_details_json, {})
            rules = details.get("rules", []) if isinstance(details, dict) else []
            return {
                "grade": grade,
                "lesson": lesson,
                "series": series_name(grade),
                "title": les.title,
                "theme": les.theme,
                "allowed_grammar": _loads(les.allowed_grammar, {}),
                "forbidden_grammar": _loads(les.forbidden_grammar, {}),
                "grammar_focus": details.get("focus")
                if isinstance(details, dict)
                else None,
                "grammar_formulas": [
                    {
                        "structure": r.get("structure"),
                        "formula": r.get("formula"),
                        "examples": r.get("examples", []),
                    }
                    for r in rules
                    if isinstance(r, dict)
                ],
                "communicative_functions": [
                    {"structure": r.get("structure"), "function": r.get("usage")}
                    for r in rules
                    if isinstance(r, dict) and r.get("usage")
                ],
                "writing_skills": _loads(les.writing_skills_json),
                "vocabulary_development": _loads(les.vocab_development_json),
                "see_also": _loads(les.see_also_json),
                "vocabulary": [
                    {
                        "word": v.word,
                        "lemma": v.lemma,
                        "pos": v.pos,
                        "section": v.section_source,
                        "definition_fa": v.definition_fa,
                        "definition_en": v.definition_en,
                        "example_en": v.example_en,
                    }
                    for v in vocab
                ],
                "cumulative_vocabulary_size": len(
                    self.index.allowed_words((grade, lesson))
                ),
            }

    def search_curriculum(
        self, query: str, grade: int | None = None, limit: int = 5
    ) -> list[dict[str, Any]]:
        if grade is not None:
            self._check_grade(grade)
        hits = hybrid_search_passages(
            self.engine,
            query,
            max_grade=grade or 12,
            max_lesson=99,
            top_k=1000,
        )
        return [
            {
                "grade": h["grade"],
                "lesson": h["lesson_num"],
                "section_type": h["section_type"],
                "title": h["title"],
                "content": h["content"],
                "score": h["hybrid_score"],
            }
            for h in hits
            if grade is None or h["grade"] == grade
        ][: _clamp_limit(limit)]

    def retrieve_exam_questions(
        self,
        section: str | None = None,
        topic: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        rows = retrieve_exam_items(
            self.engine,
            grade=12,
            sections=[section.lower()] if section else None,
            query=topic or None,
            top_k=_clamp_limit(limit),
        )
        return [
            {
                "id": r["id"],
                "year": r["shamsi_year"],
                "session": r["session"],
                "section": r["section_code"],
                "item_type": r["item_type"],
                "lesson": r["lesson_num"],
                "bloom_level": r["bloom_level"],
                "difficulty": r["difficulty"],
                "points": r["points"],
                "instruction": r["instruction_en"],
                "stem": r["stem_text"],
                "passage": r["passage_text"],
                "options": _loads(r["options_json"], []),
                "answer": r["canonical_answer"],
                "acceptable_variants": _loads(r["acceptable_variants_json"], []),
                "rubric": _loads(r["rubric_breakdown_json"], {}),
                "distractor_rationale": r["distractor_analysis"],
                "distractor_status": r["distractor_status"],
                "concept_ids": r["concept_ids"],
                "relevance": r["hybrid_score"],
            }
            for r in rows
        ]

    def get_l1_interference(self, category: str | None = None) -> list[dict[str, Any]]:
        stmt = (
            select(L1ErrorPattern, ConceptNode)
            .join(ConceptNode, L1ErrorPattern.concept_id == ConceptNode.id)
            .order_by(L1ErrorPattern.id)
        )
        if category:
            cat = category.strip().lower()
            stmt = stmt.where(
                or_(
                    func.lower(ConceptNode.category) == cat,
                    ConceptNode.id.icontains(cat, autoescape=True),
                    ConceptNode.title_en.icontains(cat, autoescape=True),
                    L1ErrorPattern.incorrect_pattern_en.icontains(cat, autoescape=True),
                )
            )
        with session_scope(self.engine) as session:
            rows = session.execute(stmt).all()
        return [
            {
                "id": p.id,
                "concept_id": p.concept_id,
                "category": n.category,
                "concept_title_en": n.title_en,
                "error_title_fa": p.error_title_fa,
                "incorrect_pattern": p.incorrect_pattern_en,
                "correct_pattern": p.correct_pattern_en,
                "l1_root_cause_fa": p.l1_root_cause_fa,
                "distractor_drill_template": p.remedial_drill_template,
            }
            for p, n in rows
        ]

    # ---------------------------------------------------------------- resources --
    def lesson_markdown(self, grade: int, lesson: int) -> str:
        info = self.get_lesson_bounds(grade, lesson)
        with session_scope(self.engine) as session:
            passages = session.scalars(
                select(Passage)
                .where(Passage.grade == grade, Passage.lesson_num == lesson)
                .order_by(Passage.section_type, Passage.id)
            ).all()
            texts = [(p.section_type, p.title, p.content) for p in passages]

        lines = [
            f"# Grade {grade} ({info['series']}) - Lesson {lesson}: {info['title']}",
            "",
            f"**Theme:** {info['theme']}",
            "",
        ]
        for heading in ("Conversation", "Reading"):
            for kind, title, content in texts:
                if kind.lower() == heading.lower():
                    lines += [f"## {heading}: {title}", "", content.strip(), ""]
        for kind, title, content in texts:
            if kind.lower() not in ("conversation", "reading"):
                lines += [f"## {kind}: {title}", "", content.strip(), ""]

        lines += ["## Target vocabulary", ""]
        vocab = info["vocabulary"]
        if vocab:
            lines += ["| Word | POS | Persian | Section |", "| --- | --- | --- | --- |"]
            lines += [
                f"| {v['word']} | {v['pos']} | {v['definition_fa'] or ''} | {v['section'] or ''} |"
                for v in vocab
            ]
        else:
            lines.append("_No vocabulary recorded for this lesson._")
        lines += ["", "## Grammar summary", ""]
        if info["grammar_focus"]:
            lines += [f"**Focus:** {info['grammar_focus']}", ""]
        for rule in info["grammar_formulas"]:
            lines.append(f"- **{rule['structure']}**: `{rule['formula']}`")
            lines += [f"  - e.g. {ex}" for ex in rule["examples"]]
        for fn in info["communicative_functions"]:
            lines.append(f"- _Function ({fn['structure']}):_ {fn['function']}")
        lines += [
            "",
            f"**Allowed grammar:** `{json.dumps(info['allowed_grammar'])}`",
            "",
            f"**Not yet taught (forbidden):** `{json.dumps(info['forbidden_grammar'])}`",
            "",
        ]
        return "\n".join(lines)

    def curriculum_index_markdown(self) -> str:
        with session_scope(self.engine) as session:
            rows = session.execute(
                select(Lesson.grade, Lesson.lesson_num, Lesson.title).order_by(
                    Lesson.grade, Lesson.lesson_num
                )
            ).all()
        lines = ["# KavoshELT curriculum index", ""]
        lines += [
            f"- `curriculum://grade/{g}/lesson/{n}` - {series_name(g)} L{n}: {t}"
            for g, n, t in rows
        ]
        return "\n".join(lines) + "\n"


_service: KavoshService | None = None
_lock = threading.Lock()


def get_service(db_path: str | os.PathLike[str] | None = None) -> KavoshService:
    """Process-wide lazily created service (first call may build the database)."""
    global _service
    with _lock:
        if _service is None:
            _service = KavoshService(db_path)
        return _service
