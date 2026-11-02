from __future__ import annotations

from typing import Any

from kavosh.models import DbTarget
from kavosh.syllabus import Bound, SyllabusIndex, VocabEntry, get_index
from kavosh.validator import validate_with_index

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

MAX_ALTERNATIVES = 3


def _persian_tokens(definition: str) -> frozenset[str]:
    for sep in ("،", ",", "؛", ";", "/", "(", ")"):
        definition = definition.replace(sep, " ")
    return frozenset(definition.split())


def _persian_overlap(a: str, b: str) -> bool:
    """Whole-token containment (substring matching mis-links e.g. واکسن / سن)."""
    ta, tb = _persian_tokens(a), _persian_tokens(b)
    return bool(ta) and bool(tb) and (ta <= tb or tb <= ta)


def rank_alternatives(
    index: SyllabusIndex, word: str, bound: Bound, limit: int = MAX_ALTERNATIVES
) -> list[dict[str, Any]]:
    """Rank in-syllabus replacements for an out-of-bounds ``word``.

    Ranking: curated synonyms (in curated order) > words sharing the exact Persian
    definition > words whose Persian definition contains / is contained by it; ties
    break towards words taught earlier (more familiar to students).
    """
    w = word.lower().strip()
    allowed = index.allowed_words(bound)
    ranked: list[dict[str, Any]] = []
    seen: set[str] = {w}

    def push(entry_word: str, basis: str, entry: VocabEntry | None) -> None:
        key = entry_word.lower()
        if key in seen:
            return
        seen.add(key)
        taught = entry or index.lookup(key)
        ranked.append(
            {
                "word": entry_word,
                "basis": basis,
                "taught_in_grade": taught.grade if taught else None,
                "taught_in_lesson": taught.lesson_num if taught else None,
            }
        )

    for syn in CURATED_SYNONYMS.get(w, []):
        if syn.lower() in allowed:
            push(syn, "curated_synonym", None)

    source = index.lookup(w)
    def_fa = source.definition_fa if source else None
    if def_fa:
        for entry in index.same_definition(def_fa, bound):
            push(entry.word, "same_definition", entry)
        if len(ranked) < limit:
            for other in index.definitions():
                if other != def_fa and _persian_overlap(def_fa, other):
                    for entry in index.same_definition(other, bound):
                        push(entry.word, "related_definition", entry)
    return ranked[:limit]


def advise_words(
    index: SyllabusIndex, words: list[str], bound: Bound
) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {}
    for word in words:
        w = str(word).lower()
        row = index.lookup(w)
        alternatives = rank_alternatives(index, w, bound)
        diagnostics[word] = {
            "taught_in_grade": row.grade if row else None,
            "taught_in_lesson": row.lesson_num if row else None,
            "definition_fa": row.definition_fa if row else None,
            "in_syllabus_alternatives": [a["word"] for a in alternatives],
            "ranked_alternatives": alternatives,
        }
    return diagnostics


def analyze_and_advise(
    conn: DbTarget, max_grade: int, max_lesson: int, text: str
) -> dict[str, Any]:
    index = get_index(conn)
    validation = validate_with_index(index, max_grade, max_lesson, text)
    validation["word_diagnostics"] = advise_words(
        index, validation["out_of_syllabus_words"], (max_grade, max_lesson)
    )
    return validation
