from __future__ import annotations

from typing import Any

from sqlalchemy import and_, func, or_, select

from kavosh.models import DbTarget, Vocabulary, session_scope
from kavosh.validator import get_allowed_vocabulary, validate_exam_text

CURATED_SYNONYMS: dict[str, list[str]] = {
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
    "dwelling": ["house", "home"],
}


def analyze_and_advise(
    conn: DbTarget, max_grade: int, max_lesson: int, text: str
) -> dict[str, Any]:
    validation = validate_exam_text(conn, max_grade, max_lesson, text)
    allowed_vocab = get_allowed_vocabulary(conn, max_grade, max_lesson)

    word_diagnostics: dict[str, Any] = {}

    with session_scope(conn) as session:
        for word in validation["out_of_syllabus_words"]:
            w = str(word).lower()
            stmt = (
                select(Vocabulary)
                .where(
                    or_(
                        func.lower(Vocabulary.lemma) == w,
                        func.lower(Vocabulary.word) == w,
                    )
                )
                .order_by(Vocabulary.grade.asc(), Vocabulary.lesson_num.asc())
                .limit(1)
            )
            vocab_row: Vocabulary | None = session.scalars(stmt).first()

            taught_grade: int | None = vocab_row.grade if vocab_row else None
            taught_lesson: int | None = vocab_row.lesson_num if vocab_row else None
            def_fa: str | None = vocab_row.definition_fa if vocab_row else None

            alternatives: list[str] = []
            if w in CURATED_SYNONYMS:
                for syn in CURATED_SYNONYMS[w]:
                    if syn.lower() in allowed_vocab:
                        alternatives.append(syn)

            if not alternatives and def_fa:
                alt_stmt = (
                    select(Vocabulary.word)
                    .distinct()
                    .where(
                        and_(
                            Vocabulary.definition_fa.like(f"%{def_fa}%"),
                            or_(
                                Vocabulary.grade < max_grade,
                                and_(
                                    Vocabulary.grade == max_grade,
                                    Vocabulary.lesson_num <= max_lesson,
                                ),
                            ),
                        )
                    )
                    .limit(3)
                )
                for candidate_word in session.scalars(alt_stmt).all():
                    if candidate_word.lower() != w:
                        alternatives.append(candidate_word)

            word_diagnostics[word] = {
                "taught_in_grade": taught_grade,
                "taught_in_lesson": taught_lesson,
                "definition_fa": def_fa,
                "in_syllabus_alternatives": alternatives,
            }

    validation["word_diagnostics"] = word_diagnostics
    return validation
