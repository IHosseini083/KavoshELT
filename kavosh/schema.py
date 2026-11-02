from __future__ import annotations

import sqlite3

from sqlalchemy import text

from kavosh.models import Base, DbTarget, create_engine_for_target, session_scope

FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS passages_fts USING fts5(
    grade,
    lesson_num,
    section_type,
    title,
    content
);

CREATE VIRTUAL TABLE IF NOT EXISTS exam_items_fts USING fts5(
    item_id,
    paper_id,
    section_code,
    stem_text,
    canonical_answer,
    concept_keywords
);
"""


def init_db(target: DbTarget) -> None:
    if isinstance(target, sqlite3.Connection):
        engine = create_engine_for_target(target)
        Base.metadata.create_all(engine)
        target.executescript(FTS_SQL)
        target.commit()
        return

    with session_scope(target) as session:
        bind = session.get_bind()
        Base.metadata.create_all(bind)
        for stmt in FTS_SQL.strip().split(";"):
            clean_stmt = stmt.strip()
            if clean_stmt:
                session.execute(text(clean_stmt))
        session.commit()
