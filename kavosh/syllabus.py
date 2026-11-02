"""In-memory, indexed view of the cumulative syllabus vocabulary.

Loading the vocabulary once and answering "is this word taught by (grade, lesson)?"
with a dictionary lookup replaces a database round-trip + set rebuild per call.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import func, select

from kavosh.models import DbTarget, Lesson, Vocabulary, session_scope
from kavosh.validator_data import COMMON_PROPER_NOUNS

Bound = tuple[int, int]
"""``(grade, lesson)`` ordered lexicographically: a word taught at or before it is allowed."""

WORD_BANK_SOURCE = "word_bank"


@dataclass(frozen=True)
class VocabEntry:
    word: str
    lemma: str
    pos: str
    grade: int
    lesson_num: int
    definition_fa: str | None
    definition_en: str | None
    example_en: str | None
    section_source: str | None

    @property
    def position(self) -> Bound:
        return (self.grade, self.lesson_num)


class SyllabusIndex:
    """Immutable index built from the vocabulary and lesson tables."""

    def __init__(self, entries: Iterable[VocabEntry], lessons: Iterable[Bound]) -> None:
        self.entries: tuple[VocabEntry, ...] = tuple(
            sorted(entries, key=lambda e: (e.grade, e.lesson_num, e.lemma, e.word))
        )
        self._last_lesson: dict[int, int] = {}
        for grade, lesson in lessons:
            self._last_lesson[grade] = max(lesson, self._last_lesson.get(grade, 0))

        self._first_taught: dict[str, Bound] = {}
        self._by_form: dict[str, VocabEntry] = {}
        self._by_definition: dict[str, list[VocabEntry]] = {}
        for entry in self.entries:  # sorted => first hit is the earliest
            pos = entry.position
            for form in (entry.lemma, entry.word):
                key = form.lower().strip()
                if not key:
                    continue
                self._by_form.setdefault(key, entry)
                for part in {key, *key.split()}:
                    known = self._first_taught.get(part)
                    if known is None or pos < known:
                        self._first_taught[part] = pos
            if entry.definition_fa and entry.section_source != WORD_BANK_SOURCE:
                self._by_definition.setdefault(entry.definition_fa, []).append(entry)
        self._allowed_cache: dict[Bound, frozenset[str]] = {}
        self._lock = threading.Lock()

    @classmethod
    def from_target(cls, target: DbTarget) -> SyllabusIndex:
        with session_scope(target) as session:
            rows = session.scalars(select(Vocabulary)).all()
            entries = [
                VocabEntry(
                    word=r.word,
                    lemma=r.lemma,
                    pos=r.pos,
                    grade=r.grade,
                    lesson_num=r.lesson_num,
                    definition_fa=r.definition_fa,
                    definition_en=r.definition_en,
                    example_en=r.example_en,
                    section_source=r.section_source,
                )
                for r in rows
            ]
            lessons = [
                (g, n)
                for g, n in session.execute(select(Lesson.grade, Lesson.lesson_num))
            ]
        return cls(entries, lessons)

    # -- bounds -----------------------------------------------------------------
    def last_lesson(self, grade: int) -> int:
        """Highest lesson number of ``grade`` (0 when the grade is unknown)."""
        return self._last_lesson.get(grade, 0)

    def grade_bound(self, grade: int) -> Bound:
        return (grade, self.last_lesson(grade) or 99)

    # -- lookups ----------------------------------------------------------------
    def allowed_words(self, bound: Bound) -> frozenset[str]:
        """All lowercase forms taught up to ``bound`` plus common proper nouns."""
        cached = self._allowed_cache.get(bound)
        if cached is not None:
            return cached
        with self._lock:
            words = COMMON_PROPER_NOUNS | {
                form for form, pos in self._first_taught.items() if pos <= bound
            }
            self._allowed_cache[bound] = words
            return words

    def lookup(self, form: str) -> VocabEntry | None:
        """Earliest entry whose lemma or word equals ``form`` (case-insensitive)."""
        return self._by_form.get(form.lower().strip())

    def entries_in_scope(self, bound: Bound) -> list[VocabEntry]:
        return [e for e in self.entries if e.position <= bound]

    def same_definition(self, definition_fa: str, bound: Bound) -> list[VocabEntry]:
        """In-scope entries sharing the exact Persian definition (earliest first)."""
        return [
            e for e in self._by_definition.get(definition_fa, []) if e.position <= bound
        ]

    def definitions(self) -> list[str]:
        return list(self._by_definition)


# -- per-target cache -----------------------------------------------------------------
_CACHE_SIZE = 8
_cache: OrderedDict[tuple[object, int, int], SyllabusIndex] = OrderedDict()
_cache_lock = threading.Lock()


def _target_key(target: DbTarget) -> object:
    return target if isinstance(target, str) else id(target)


def get_index(target: DbTarget) -> SyllabusIndex:
    """Return a cached index, rebuilt whenever the vocabulary table changes size."""
    with session_scope(target) as session:
        count, max_id = session.execute(
            select(func.count(Vocabulary.id), func.max(Vocabulary.id))
        ).one()
    key = (_target_key(target), int(count or 0), int(max_id or 0))
    with _cache_lock:
        hit = _cache.get(key)
        if hit is not None:
            _cache.move_to_end(key)
            return hit
    index = SyllabusIndex.from_target(target)
    with _cache_lock:
        _cache[key] = index
        while len(_cache) > _CACHE_SIZE:
            _cache.popitem(last=False)
    return index
