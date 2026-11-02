"""Typed SQLAlchemy access to the FTS5 virtual tables (no raw SQL strings)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import column, func, literal_column, select, table
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

passages_fts = table(
    "passages_fts",
    column("grade"),
    column("lesson_num"),
    column("section_type"),
    column("title"),
    column("content"),
)
exam_items_fts = table(
    "exam_items_fts",
    column("item_id"),
    column("paper_id"),
    column("section_code"),
    column("stem_text"),
    column("canonical_answer"),
    column("concept_keywords"),
)


class FtsQueryError(ValueError):
    """Raised when a user-supplied FTS5 expression is syntactically invalid."""


def search_passages(
    session: Session, query: str, limit: int = 5
) -> list[dict[str, Any]]:
    """BM25-ranked FTS5 search over textbook passages (``query`` uses FTS5 syntax)."""
    stmt = (
        select(
            passages_fts.c.grade,
            passages_fts.c.lesson_num,
            passages_fts.c.section_type,
            passages_fts.c.title,
            passages_fts.c.content,
        )
        .where(literal_column("passages_fts").op("MATCH")(query))
        .order_by(literal_column("rank"))
        .limit(limit)
    )
    try:
        rows = session.execute(stmt).all()
    except OperationalError as exc:
        raise FtsQueryError(f"Invalid full-text query {query!r}: {exc.orig}") from exc
    return [
        {
            "grade": r[0],
            "lesson_num": r[1],
            "section_type": r[2],
            "title": r[3],
            "content": r[4],
        }
        for r in rows
    ]


def count_passages(session: Session, grade: int | None = None) -> int:
    stmt = select(func.count()).select_from(passages_fts)
    if grade is not None:
        stmt = stmt.where(passages_fts.c.grade == str(grade))
    return int(session.scalar(stmt) or 0)
