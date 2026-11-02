from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
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
    grammar_details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    writing_skills_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    vocab_development_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    see_also_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class Vocabulary(Base):
    __tablename__ = "vocabulary"
    __table_args__ = (
        UniqueConstraint(
            "lemma", "grade", "lesson_num", name="uq_vocab_lemma_grade_lesson"
        ),
        Index("idx_vocab_lemma", "lemma"),
        Index("idx_vocab_scope", "grade", "lesson_num"),
        Index("idx_vocab_source", "section_source"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(128), nullable=False)
    lemma: Mapped[str] = mapped_column(String(128), nullable=False)
    pos: Mapped[str] = mapped_column(String(32), nullable=False)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)
    lesson_num: Mapped[int] = mapped_column(Integer, nullable=False)
    definition_fa: Mapped[str | None] = mapped_column(Text, nullable=True)
    definition_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    example_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    section_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    embedding_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class Passage(Base):
    __tablename__ = "passages"
    __table_args__ = (Index("idx_passages_scope", "grade", "lesson_num"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)
    lesson_num: Mapped[int] = mapped_column(Integer, nullable=False)
    section_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class Rubric(Base):
    __tablename__ = "rubrics"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)
    term: Mapped[int] = mapped_column(Integer, nullable=False)
    exam_type: Mapped[str] = mapped_column(String(64), nullable=False)
    total_points: Mapped[float] = mapped_column(Float, nullable=False)
    structure_json: Mapped[str] = mapped_column(Text, nullable=False)


class ConceptNode(Base):
    __tablename__ = "concept_nodes"
    __table_args__ = (
        Index("idx_concept_grade_lesson", "grade", "lesson_num"),
        Index("idx_concept_category", "category"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)
    lesson_num: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    title_en: Mapped[str] = mapped_column(String(255), nullable=False)
    title_fa: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class ConceptEdge(Base):
    __tablename__ = "concept_edges"
    __table_args__ = (
        Index("idx_edge_source", "source_id"),
        Index("idx_edge_target", "target_id"),
        Index("idx_edge_relation", "relation_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("concept_nodes.id", ondelete="CASCADE"), nullable=False
    )
    target_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("concept_nodes.id", ondelete="CASCADE"), nullable=False
    )
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class NationalExamPaper(Base):
    __tablename__ = "national_exam_papers"
    __table_args__ = (Index("idx_paper_year_session", "shamsi_year", "session"),)

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)
    shamsi_year: Mapped[int] = mapped_column(Integer, nullable=False)
    session: Mapped[str] = mapped_column(String(32), nullable=False)
    total_written_points: Mapped[float] = mapped_column(Float, nullable=False)
    blueprint_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_origin: Mapped[str] = mapped_column(String(128), default="Markaz-e-Sanjesh")
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True)


class ExamQuestionItem(Base):
    __tablename__ = "exam_question_items"
    __table_args__ = (
        Index("idx_item_paper", "paper_id"),
        Index("idx_item_scope", "grade", "lesson_num", "section_code"),
        Index("idx_item_type", "item_type"),
        Index("idx_item_difficulty", "difficulty"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    paper_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("national_exam_papers.id", ondelete="CASCADE"),
        nullable=False,
    )
    section_code: Mapped[str] = mapped_column(String(32), nullable=False)
    item_type: Mapped[str] = mapped_column(String(32), nullable=False)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)
    lesson_num: Mapped[int] = mapped_column(Integer, nullable=False)
    bloom_level: Mapped[str] = mapped_column(String(32), default="apply")
    difficulty: Mapped[str] = mapped_column(String(16), default="medium")
    points: Mapped[float] = mapped_column(Float, nullable=False)
    instruction_en: Mapped[str] = mapped_column(Text, nullable=False)
    stem_text: Mapped[str] = mapped_column(Text, nullable=False)
    passage_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    options_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical_answer: Mapped[str] = mapped_column(Text, nullable=False)
    acceptable_variants_json: Mapped[str] = mapped_column(Text, default="[]")
    rubric_breakdown_json: Mapped[str] = mapped_column(Text, default="{}")
    distractor_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Provenance of ``distractor_analysis``: NULL = authored with the item,
    # "machine_drafted" = drafted from the item and key, awaiting teacher review.
    distractor_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    concept_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    embedding_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_synthetic_twin: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_item_id: Mapped[str | None] = mapped_column(String(128), nullable=True)


class L1ErrorPattern(Base):
    __tablename__ = "l1_error_patterns"
    __table_args__ = (Index("idx_l1_concept", "concept_id"),)

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    concept_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("concept_nodes.id", ondelete="CASCADE"), nullable=False
    )
    error_title_fa: Mapped[str] = mapped_column(String(255), nullable=False)
    incorrect_pattern_en: Mapped[str] = mapped_column(Text, nullable=False)
    correct_pattern_en: Mapped[str] = mapped_column(Text, nullable=False)
    l1_root_cause_fa: Mapped[str] = mapped_column(Text, nullable=False)
    remedial_drill_template: Mapped[str] = mapped_column(Text, nullable=False)


DbTarget = str | Engine | Session | sqlite3.Connection

_CONN_ENGINE_CACHE: dict[int, tuple[sqlite3.Connection, Engine]] = {}


def create_engine_for_target(target: str | sqlite3.Connection) -> Engine:
    if isinstance(target, sqlite3.Connection):
        conn_id = id(target)
        cached = _CONN_ENGINE_CACHE.get(conn_id)
        if cached is not None and cached[0] is target:
            return cached[1]
        engine = create_engine(
            "sqlite://",
            creator=lambda: target,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        if len(_CONN_ENGINE_CACHE) > 32:
            _CONN_ENGINE_CACHE.clear()
        _CONN_ENGINE_CACHE[conn_id] = (target, engine)
        return engine
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
        engine = create_engine_for_target(target)
        factory = sessionmaker(bind=engine, expire_on_commit=False)
        sess = factory()
        try:
            yield sess
            sess.commit()
        finally:
            sess.close()
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
