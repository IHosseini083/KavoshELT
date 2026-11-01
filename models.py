from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator, Optional, Union

from sqlalchemy import Float, Index, Integer, String, Text, UniqueConstraint, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


class Lesson(Base):
    __tablename__ = "lessons"

    grade: Mapped[int] = mapped_column(Integer, primary_key=True)
    lesson_num: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    theme: Mapped[str] = mapped_column(Text, nullable=False)
    allowed_grammar: Mapped[str] = mapped_column(Text, nullable=False)
    forbidden_grammar: Mapped[str] = mapped_column(Text, nullable=False)


class Vocabulary(Base):
    __tablename__ = "vocabulary"
    __table_args__ = (
        UniqueConstraint("lemma", "grade", "lesson_num", name="uq_vocab_lemma_grade_lesson"),
        Index("idx_vocab_lemma", "lemma"),
        Index("idx_vocab_scope", "grade", "lesson_num"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(128), nullable=False)
    lemma: Mapped[str] = mapped_column(String(128), nullable=False)
    pos: Mapped[str] = mapped_column(String(32), nullable=False)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)
    lesson_num: Mapped[int] = mapped_column(Integer, nullable=False)
    definition_fa: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    example_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Passage(Base):
    __tablename__ = "passages"
    __table_args__ = (
        Index("idx_passages_scope", "grade", "lesson_num"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)
    lesson_num: Mapped[int] = mapped_column(Integer, nullable=False)
    section_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Rubric(Base):
    __tablename__ = "rubrics"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)
    term: Mapped[int] = mapped_column(Integer, nullable=False)
    exam_type: Mapped[str] = mapped_column(String(64), nullable=False)
    total_points: Mapped[float] = mapped_column(Float, nullable=False)
    structure_json: Mapped[str] = mapped_column(Text, nullable=False)


DbTarget = Union[str, Engine, Session, sqlite3.Connection]


def create_engine_for_target(target: Union[str, sqlite3.Connection]) -> Engine:
    if isinstance(target, sqlite3.Connection):
        return create_engine(
            "sqlite://",
            creator=lambda: target,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
    if target == ":memory:":
        return create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
    return create_engine(f"sqlite:///{target}")


@contextmanager
def session_scope(target: DbTarget) -> Iterator[Session]:
    if isinstance(target, Session):
        yield target
        return
    if isinstance(target, Engine):
        factory = sessionmaker(bind=target, expire_on_commit=False)
        sess = factory()
        try:
            yield sess
            sess.commit()
        finally:
            sess.close()
        return

    if isinstance(target, sqlite3.Connection):
        engine = create_engine(
            "sqlite://",
            creator=lambda: target,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        factory = sessionmaker(bind=engine, expire_on_commit=False)
        sess = factory()
        try:
            yield sess
            sess.commit()
        finally:
            sess.close()
            # Do NOT dispose engine here as it closes the caller's connection
        return

    engine = create_engine_for_target(target)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    sess = factory()
    try:
        yield sess
        sess.commit()
    finally:
        sess.close()
        engine.dispose()
