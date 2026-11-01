import sqlite3

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS lessons (
    grade INTEGER NOT NULL,
    lesson_num INTEGER NOT NULL,
    title TEXT NOT NULL,
    theme TEXT NOT NULL,
    allowed_grammar TEXT NOT NULL,
    forbidden_grammar TEXT NOT NULL,
    PRIMARY KEY (grade, lesson_num)
);

CREATE TABLE IF NOT EXISTS vocabulary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL,
    lemma TEXT NOT NULL,
    pos TEXT NOT NULL,
    grade INTEGER NOT NULL,
    lesson_num INTEGER NOT NULL,
    definition_fa TEXT,
    example_en TEXT,
    UNIQUE(lemma, grade, lesson_num)
);

CREATE INDEX IF NOT EXISTS idx_vocab_lemma ON vocabulary(lemma);
CREATE INDEX IF NOT EXISTS idx_vocab_scope ON vocabulary(grade, lesson_num);

CREATE VIRTUAL TABLE IF NOT EXISTS passages_fts USING fts5(
    grade,
    lesson_num,
    section_type,
    title,
    content
);

CREATE TABLE IF NOT EXISTS rubrics (
    id TEXT PRIMARY KEY,
    grade INTEGER NOT NULL,
    term INTEGER NOT NULL,
    exam_type TEXT NOT NULL,
    total_points REAL NOT NULL,
    structure_json TEXT NOT NULL
);
"""

def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()
