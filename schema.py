from __future__ import annotations

import sqlite3
from sqlalchemy import text
from models import Base, DbTarget, create_engine_for_target, session_scope

FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS passages_fts USING fts5(
    grade,
    lesson_num,
    section_type,
    title,
    content
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
        session.execute(text(FTS_SQL))
        session.commit()
