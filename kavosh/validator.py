from __future__ import annotations

import re
from typing import Any

from kavosh.models import DbTarget
from kavosh.morphology import (
    CONTRACTION_MAP,
    IRREGULAR_FORMS,
    is_known_form,
)
from kavosh.syllabus import Bound, SyllabusIndex, get_index
from kavosh.validator_data import COMMON_PROPER_NOUNS

__all__ = [
    "COMMON_PROPER_NOUNS",
    "CONTRACTION_MAP",
    "IRREGULAR_VERB_MAP",
    "STOP_CONTRACTIONS",
    "check_grammar_bounds",
    "clean_markdown_and_metadata",
    "get_allowed_vocabulary",
    "lemmatize_word",
    "tokenize",
    "validate_exam_text",
    "validate_with_index",
]

IRREGULAR_VERB_MAP: dict[str, str] = IRREGULAR_FORMS
"""Backward-compatible alias of :data:`kavosh.morphology.IRREGULAR_FORMS`."""

STOP_CONTRACTIONS: frozenset[str] = frozenset(
    {"'s", "'re", "'m", "'ve", "'ll", "'d", "n't", "s", "d", "t"}
)

_NOT_PARTICIPLE = (
    r"(?!(?:red|bed|shed|need|seed|feed|speed|weed|breed|hundred|indeed|sacred|"
    r"naked|wicked)\b)"
)
_RE_PRESENT_PERF = re.compile(
    r"\b(?:have|has|haven't|hasn't)\s+"
    + _NOT_PARTICIPLE
    + r"(\w{2,}ed|been|seen|done|gone|taken|written|eaten|given|known|chosen|"
    r"spoken|broken|driven|fallen|grown|shown|worn|begun|found|built|made|"
    r"lived|worked|dedicated)\b",
    re.IGNORECASE,
)
_NOT_ING_NOUN = (
    r"(?!(?:nothing|something|anything|everything|morning|evening|building|"
    r"wedding|ceiling|boring|interesting|amazing|exciting|tiring|surprising|"
    r"relaxing|shocking|frightening|terrifying|embarrassing|confusing|"
    r"disappointing|during|spring|string|bring)\b)"
)
_RE_PAST_PROG = re.compile(
    r"\b(was|were|wasn't|weren't)\s+" + _NOT_ING_NOUN + r"(\w{2,}ing)\b",
    re.IGNORECASE,
)
_RE_PASSIVE = re.compile(
    r"\b(is|are|was|were|be|been|being)\s+(\w+ed|\w+en|built|made|done|seen|taken|found|developed)\s+by\b|\b(is|are|was|were)\s+being\s+\w+",
    re.IGNORECASE,
)
_RE_COND2 = re.compile(r"\bif\b[^\.\?!;]+?\bwould\b", re.IGNORECASE)

_RE_CODE_FENCE = re.compile(r"```[a-zA-Z]*")
_RE_TAG = re.compile(r"<[^>]+>")
_RE_BRACKET = re.compile(r"\[[^\]]+\]")
_RE_PERSIAN = re.compile(r"[\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]")
_RE_MARKDOWN_SYM = re.compile(r"[*#_`|~=>\-]")
_RE_TOKENIZE = re.compile(r"\b[A-Za-z]+(?:'[A-Za-z]+)?\b")
_RE_APOSTROPHES = re.compile(r"[\u2018\u2019\u02bc`\u00b4]")
_CLITICS = ("'s", "'re", "'m", "'ve", "'ll", "'d")


def get_allowed_vocabulary(
    conn: DbTarget, max_grade: int = 10, max_lesson: int = 4
) -> set[str]:
    """Lowercase word forms taught up to ``(max_grade, max_lesson)`` (inclusive)."""
    return set(get_index(conn).allowed_words((max_grade, max_lesson)))


def lemmatize_word(word: str, allowed_set: set[str]) -> bool:
    """True when ``word`` is allowed directly or as an inflection of an allowed word."""
    w = word.lower().strip()
    return is_known_form(w, allowed_set | COMMON_PROPER_NOUNS)


def _stem_for_check(token: str) -> str:
    """Strip clitics (``it's``, ``I'm``, ``isn't``) so only the host word is checked."""
    t = token.lower()
    if t in CONTRACTION_MAP:
        return t
    if t.endswith("n't"):
        return t[:-3]
    for clitic in _CLITICS:
        if t.endswith(clitic):
            return t[: -len(clitic)]
    return t.strip("'")


def tokenize(text: str) -> list[str]:
    """Return the English word tokens of ``text`` after stripping markup/Persian."""
    cleaned = clean_markdown_and_metadata(_RE_APOSTROPHES.sub("'", text))
    return _RE_TOKENIZE.findall(cleaned)


def check_grammar_bounds(
    text: str, max_grade: int, max_lesson: int
) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    clean_text = _RE_APOSTROPHES.sub("'", text).replace("\n", " ")

    def add(kind: str, match: re.Match[str], reason: str) -> None:
        hits.append({"type": kind, "match": match.group(0), "reason": reason})

    if max_grade < 11:
        for m in _RE_PRESENT_PERF.finditer(clean_text):
            add(
                "present_perfect",
                m,
                f"Present Perfect is forbidden in Grade {max_grade} (introduced in Grade 11 Vision 2).",
            )

    if max_grade < 10 or (max_grade == 10 and max_lesson < 3):
        for m in _RE_PAST_PROG.finditer(clean_text):
            add(
                "past_progressive",
                m,
                "Past Progressive is forbidden before Grade 10 Lesson 3.",
            )

    if max_grade < 12:
        for m in _RE_PASSIVE.finditer(clean_text):
            add(
                "passive_voice",
                m,
                f"Passive Voice is forbidden in Grade {max_grade} (introduced in Grade 12 Vision 3).",
            )

    if max_grade < 12 or (max_grade == 12 and max_lesson < 2):
        for m in _RE_COND2.finditer(clean_text):
            add(
                "conditional_type_2",
                m,
                "Conditional Type 2 is forbidden before Grade 12 Lesson 2.",
            )

    return hits


def clean_markdown_and_metadata(text: str) -> str:
    t = _RE_CODE_FENCE.sub("", text)
    t = _RE_TAG.sub(" ", t)
    t = _RE_BRACKET.sub(" ", t)
    t = _RE_PERSIAN.sub(" ", t)
    return _RE_MARKDOWN_SYM.sub(" ", t)


def validate_with_index(
    index: SyllabusIndex, max_grade: int, max_lesson: int, text: str
) -> dict[str, Any]:
    """Validate ``text`` against an already-built :class:`SyllabusIndex`."""
    bound: Bound = (max_grade, max_lesson)
    allowed = index.allowed_words(bound)
    raw_tokens = tokenize(text)

    out_of_syllabus: list[str] = []
    seen: set[str] = set()
    for token in raw_tokens:
        stem = _stem_for_check(token)
        if not stem or stem in STOP_CONTRACTIONS or stem.isdigit() or stem in seen:
            continue
        if not is_known_form(stem, allowed):
            seen.add(stem)
            out_of_syllabus.append(stem)

    grammar_hits = check_grammar_bounds(text, max_grade, max_lesson)
    return {
        "is_valid": not out_of_syllabus and not grammar_hits,
        "max_grade": max_grade,
        "max_lesson": max_lesson,
        "out_of_syllabus_words": out_of_syllabus,
        "forbidden_grammar_hits": grammar_hits,
        "word_count": len(raw_tokens),
    }


def validate_exam_text(
    conn: DbTarget, max_grade: int, max_lesson: int, text: str
) -> dict[str, Any]:
    return validate_with_index(get_index(conn), max_grade, max_lesson, text)
