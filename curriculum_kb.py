#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from typing import Any, Dict, List, Optional

from advisor import analyze_and_advise
from auditor import run_curriculum_audit
from exam_generator import generate_full_exam_package
from exam_styler import (
    generate_answer_key_pdf,
    generate_exam_docx,
    generate_exam_html,
    generate_exam_pdf,
)
from exam_composer import compose_exam
from exam_rag_engine import traverse_prerequisites
from models import DbTarget
from rag import retrieve_rag_context
from validator import validate_exam_text

CURRICULUM_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "curriculum.db")
VISION1_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "vision1.db")


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    if not db_path:
        db_path = (
            CURRICULUM_DB_PATH
            if os.path.exists(CURRICULUM_DB_PATH)
            else VISION1_DB_PATH
        )
    if not os.path.exists(db_path):
        from schema import init_db
        from seed_all_grades import seed_curriculum

        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path)
        init_db(conn)
        seed_curriculum(conn)
        return conn
    return sqlite3.connect(db_path)


def cmd_context(args: argparse.Namespace) -> None:
    conn = get_connection(args.db)
    lessons = [int(x.strip()) for x in args.lessons.split(",") if x.strip()]
    cur = conn.cursor()

    placeholders = ",".join("?" for _ in lessons)
    cur.execute(
        f"SELECT lesson_num, title, theme, allowed_grammar, forbidden_grammar FROM lessons WHERE grade = ? AND lesson_num IN ({placeholders}) ORDER BY lesson_num",
        [args.grade] + lessons,
    )
    lessons_data = []
    for row in cur.fetchall():
        lessons_data.append(
            {
                "lesson_num": row[0],
                "title": row[1],
                "theme": row[2],
                "allowed_grammar": json.loads(row[3]),
                "forbidden_grammar": json.loads(row[4]),
            }
        )

    cur.execute(
        f"SELECT word, lemma, pos, definition_fa, example_en, lesson_num FROM vocabulary WHERE grade = ? AND lesson_num IN ({placeholders}) ORDER BY lesson_num, word",
        [args.grade] + lessons,
    )
    vocab_data = [
        {
            "word": r[0],
            "lemma": r[1],
            "pos": r[2],
            "definition_fa": r[3],
            "example_en": r[4],
            "lesson_num": r[5],
        }
        for r in cur.fetchall()
    ]

    term = (
        1
        if max(lessons)
        <= (
            4
            if args.grade == 7
            else 3
            if args.grade == 8
            else 3
            if args.grade == 9
            else 2
        )
        else 2
    )
    cur.execute(
        "SELECT id, exam_type, total_points, structure_json FROM rubrics WHERE grade = ? AND term = ?",
        (args.grade, term),
    )
    rubric_row = cur.fetchone()
    rubric_data = None
    if rubric_row:
        rubric_data = {
            "id": rubric_row[0],
            "exam_type": rubric_row[1],
            "total_points": rubric_row[2],
            "structure": json.loads(rubric_row[3]),
        }

    output = {
        "grade": args.grade,
        "requested_lessons": lessons,
        "lessons": lessons_data,
        "vocabulary_count": len(vocab_data),
        "vocabulary": vocab_data,
        "rubric": rubric_data,
    }
    conn.close()
    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_search(args: argparse.Namespace) -> None:
    conn = get_connection(args.db)
    cur = conn.cursor()

    query = args.query.strip()
    cur.execute(
        "SELECT grade, lesson_num, section_type, title, content FROM passages_fts WHERE passages_fts MATCH ? ORDER BY rank LIMIT ?",
        (query, args.limit),
    )
    rows = cur.fetchall()
    results = [
        {
            "grade": r[0],
            "lesson_num": r[1],
            "section_type": r[2],
            "title": r[3],
            "content": r[4],
        }
        for r in rows
    ]
    conn.close()
    print(
        json.dumps(
            {"query": query, "count": len(results), "passages": results},
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_validate(args: argparse.Namespace) -> None:
    conn = get_connection(args.db)
    text = args.text
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()

    if not text:
        conn.close()
        print(
            json.dumps(
                {"error": "No text provided. Use --text or --file."}, ensure_ascii=False
            )
        )
        sys.exit(1)

    res = validate_exam_text(
        conn, max_grade=args.grade, max_lesson=args.max_lesson, text=text
    )
    conn.close()
    print(json.dumps(res, ensure_ascii=False, indent=2))


def cmd_stats(args: argparse.Namespace) -> None:
    conn = get_connection(args.db)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(DISTINCT grade), COUNT(*) FROM lessons")
    grades_count, lessons_count = cur.fetchone()

    cur.execute("SELECT COUNT(*) FROM vocabulary")
    total_vocab = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM passages_fts")
    total_passages = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM rubrics")
    total_rubrics = cur.fetchone()[0]

    print("=" * 70)
    print("Iranian Secondary English Curriculum Knowledge Base (Grades 7-12)")
    print("=" * 70)
    print(
        f"Total Grades: {grades_count:2d} | Lessons: {lessons_count:2d} | Total Vocabulary: {total_vocab:4d} | Passages: {total_passages:2d} | Rubrics: {total_rubrics:2d}\n"
    )
    print(
        f"{'Grade':<8} | {'Series':<10} | {'Lessons':<8} | {'Vocabulary':<12} | {'Passages':<8}"
    )
    print("-" * 56)

    for g in range(7, 13):
        series = f"Prospect {g - 6}" if g <= 9 else f"Vision {g - 9}"
        cur.execute("SELECT COUNT(*) FROM lessons WHERE grade = ?", (g,))
        l_cnt = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM vocabulary WHERE grade = ?", (g,))
        v_cnt = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM passages_fts WHERE grade = ?", (str(g),))
        p_cnt = cur.fetchone()[0]
        print(f"Grade {g:<2} | {series:<10} | {l_cnt:<8} | {v_cnt:<12} | {p_cnt:<8}")
    print("=" * 70)
    conn.close()


def cmd_audit(args: argparse.Namespace) -> None:
    conn = get_connection(args.db)
    report = run_curriculum_audit(conn)
    conn.close()
    print(json.dumps(report, ensure_ascii=False, indent=2))


def cmd_adapt(args: argparse.Namespace) -> None:
    conn = get_connection(args.db)
    text = args.text
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
    if not text:
        conn.close()
        print(
            json.dumps(
                {"error": "No text provided. Use --text or --file."}, ensure_ascii=False
            )
        )
        sys.exit(1)

    res = analyze_and_advise(
        conn, max_grade=args.grade, max_lesson=args.max_lesson, text=text
    )
    conn.close()
    print(json.dumps(res, ensure_ascii=False, indent=2))


def cmd_blueprint(args: argparse.Namespace) -> None:
    conn = get_connection(args.db)
    cur = conn.cursor()

    cur.execute(
        "SELECT id, exam_type, total_points, structure_json FROM rubrics WHERE grade = ? AND term = ?",
        (args.grade, args.term),
    )
    r = cur.fetchone()
    structure = json.loads(r[3]) if r else {}

    series_name = (
        f"Prospect {args.grade - 6}" if args.grade <= 9 else f"Vision {args.grade - 9}"
    )

    blueprint = {
        "title": f"Official Curriculum Blueprint - Grade {args.grade} ({series_name}) Term {args.term}",
        "grade": args.grade,
        "term": args.term,
        "exam_type": args.exam_type,
        "total_points": r[2] if r else 10.0,
        "official_rubric": structure,
        "tts_template": {
            "model": "Gemini 3.8 Flash TTS",
            "voice_config": {
                "speaker_1": {"role": "Examiner / Female Character", "voice": "Fola"},
                "speaker_2": {"role": "Male Character / Co-examiner", "voice": "Rami"},
            },
            "pacing_rules": {
                "wpm_target": "125-135 WPM",
                "pause_between_turns": "<short pause>",
                "pause_between_sections": "<long pause>",
            },
        },
    }
    conn.close()
    print(json.dumps(blueprint, ensure_ascii=False, indent=2))


def cmd_rag(args: argparse.Namespace) -> None:
    conn = get_connection(args.db)
    res = retrieve_rag_context(
        conn,
        query=args.query,
        max_grade=args.grade,
        max_lesson=args.max_lesson,
        top_k_passages=args.top_passages,
        top_k_vocab=args.top_vocab,
    )
    conn.close()
    print(json.dumps(res, ensure_ascii=False, indent=2))


def cmd_export(args: argparse.Namespace) -> None:
    fmt = args.format.lower()
    out = args.out
    if not out:
        base, _ = os.path.splitext(args.file)
        out = f"{base}.{fmt}"

    if fmt == "pdf":
        generate_exam_pdf(args.file, out, school_name=args.school)
        if args.include_key:
            key_out = out.replace(".pdf", "_answer_key.pdf")
            generate_answer_key_pdf(args.file, key_out, school_name=args.school)
    elif fmt == "docx":
        generate_exam_docx(args.file, out, school_name=args.school)
    elif fmt == "html":
        generate_exam_html(args.file, out, school_name=args.school)
    else:
        print(f"Unsupported format: {fmt}. Choose 'pdf', 'docx', or 'html'.")
        sys.exit(1)


def cmd_generate(args: argparse.Namespace) -> None:
    conn = get_connection(args.db)
    res = generate_full_exam_package(
        conn,
        grade=args.grade,
        term=args.term,
        out_dir=args.out_dir,
        school_name=args.school,
    )
    conn.close()
    print(json.dumps(res, ensure_ascii=False, indent=2))


def cmd_compose_exam(args: argparse.Namespace) -> None:
    conn = get_connection(args.db)
    lessons = (
        [int(x.strip()) for x in args.lessons.split(",") if x.strip()]
        if args.lessons
        else None
    )
    res = compose_exam(
        conn,
        mode=args.mode,
        grade=args.grade,
        lessons=lessons,
        section=args.section,
        target_points=float(args.points),
        sourcing=args.sourcing,
        school_name=args.school,
        teacher_name=args.teacher,
        out_dir=args.out_dir,
    )
    conn.close()
    print(json.dumps(res, ensure_ascii=False, indent=2))


def cmd_graph_query(args: argparse.Namespace) -> None:
    conn = get_connection(args.db)
    res = traverse_prerequisites(conn, concept_id=args.concept)
    conn.close()
    print(json.dumps(res, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Secondary English Curriculum Knowledge Base & Authoring CLI"
    )
    parser.add_argument("--db", default=None, help="Custom SQLite path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # stats
    p_stat = subparsers.add_parser(
        "stats", help="Overview of full 6-grade curriculum database"
    )
    p_stat.set_defaults(func=cmd_stats)

    # audit
    p_aud = subparsers.add_parser(
        "audit", help="Run full self-consistency audit on all lessons"
    )
    p_aud.set_defaults(func=cmd_audit)

    # context
    p_ctx = subparsers.add_parser(
        "context", help="Extract curriculum bounds and vocabulary"
    )
    p_ctx.add_argument("--grade", type=int, default=10, help="Grade level (7-12)")
    p_ctx.add_argument(
        "--lessons", default="1,2", help="Comma-separated lesson numbers"
    )
    p_ctx.set_defaults(func=cmd_context)

    # search
    p_search = subparsers.add_parser(
        "search", help="Search canonical textbook passages"
    )
    p_search.add_argument("--query", required=True, help="Search query (FTS5 syntax)")
    p_search.add_argument("--limit", type=int, default=5, help="Max results")
    p_search.set_defaults(func=cmd_search)

    # rag
    p_rag = subparsers.add_parser(
        "rag", help="Hybrid semantic + lexical RAG retrieval with syllabus guardrails"
    )
    p_rag.add_argument("--query", required=True, help="Topic or text to search for")
    p_rag.add_argument(
        "--grade", type=int, default=10, help="Maximum grade boundary (7-12)"
    )
    p_rag.add_argument(
        "--max-lesson", type=int, default=4, help="Maximum lesson boundary"
    )
    p_rag.add_argument(
        "--top-passages", type=int, default=3, help="Number of passages to retrieve"
    )
    p_rag.add_argument(
        "--top-vocab",
        type=int,
        default=15,
        help="Number of vocabulary items to retrieve",
    )
    p_rag.set_defaults(func=cmd_rag)

    # validate
    p_val = subparsers.add_parser(
        "validate", help="Validate exam text against syllabus bounds"
    )
    p_val.add_argument("--grade", type=int, default=10, help="Grade level (7-12)")
    p_val.add_argument(
        "--max-lesson", type=int, default=4, help="Maximum taught lesson index"
    )
    p_val.add_argument("--text", help="Exam text to validate")
    p_val.add_argument("--file", help="Path to markdown or text file")
    p_val.set_defaults(func=cmd_validate)

    # adapt
    p_adp = subparsers.add_parser(
        "adapt", help="Validate text and provide in-syllabus replacement advice"
    )
    p_adp.add_argument("--grade", type=int, default=10, help="Grade level (7-12)")
    p_adp.add_argument(
        "--max-lesson", type=int, default=4, help="Maximum taught lesson index"
    )
    p_adp.add_argument("--text", help="Text to adapt")
    p_adp.add_argument("--file", help="Path to file")
    p_adp.set_defaults(func=cmd_adapt)

    # blueprint
    p_bp = subparsers.add_parser(
        "blueprint", help="Generate exam blueprint and TTS specs"
    )
    p_bp.add_argument("--grade", type=int, default=10, help="Grade level (7-12)")
    p_bp.add_argument(
        "--term", type=int, choices=[1, 2], default=1, help="Term (1 or 2)"
    )
    p_bp.add_argument("--exam-type", default="Listening", help="Listening or Written")
    p_bp.set_defaults(func=cmd_blueprint)

    # export
    p_exp = subparsers.add_parser(
        "export", help="Export exam markdown to printable PDF, Word DOCX, or HTML"
    )
    p_exp.add_argument("--file", required=True, help="Input markdown exam file")
    p_exp.add_argument(
        "--format", choices=["pdf", "docx", "html"], default="pdf", help="Output format"
    )
    p_exp.add_argument("--out", help="Output file path")
    p_exp.add_argument(
        "--school", default="دبیرستان نمونه دولتی", help="School name on header"
    )
    p_exp.add_argument(
        "--include-key",
        action="store_true",
        help="Also generate separate Teacher Answer Key PDF",
    )
    p_exp.set_defaults(func=cmd_export)

    # generate
    p_gen = subparsers.add_parser(
        "generate", help="Generate complete exam package (MD + PDF + DOCX + HTML + Key)"
    )
    p_gen.add_argument("--grade", type=int, default=10, help="Grade level (7-12)")
    p_gen.add_argument(
        "--term", type=int, choices=[1, 2], default=1, help="Term (1 or 2)"
    )
    p_gen.add_argument("--out-dir", default="exports", help="Output directory")
    p_gen.add_argument(
        "--school", default="دبیرستان نمونه دولتی", help="School name on header"
    )
    p_gen.set_defaults(func=cmd_generate)

    # compose-exam
    p_comp = subparsers.add_parser(
        "compose-exam", help="Compose exam via Graph-RAG engine across 4 modes"
    )
    p_comp.add_argument(
        "--mode",
        choices=["full_mock", "skill_worksheet", "custom_quiz"],
        default="full_mock",
        help="Composition mode",
    )
    p_comp.add_argument("--grade", type=int, default=12, help="Grade level (7-12)")
    p_comp.add_argument("--lessons", help="Comma-separated lesson numbers")
    p_comp.add_argument(
        "--section",
        choices=["vocabulary", "grammar", "writing", "cloze", "reading"],
        help="Target section for worksheet",
    )
    p_comp.add_argument(
        "--points",
        type=float,
        default=28.0,
        help="Target total score (multiple of 0.25)",
    )
    p_comp.add_argument(
        "--sourcing",
        choices=["past_papers", "ai_twins", "hybrid"],
        default="past_papers",
        help="Question sourcing strategy",
    )
    p_comp.add_argument("--school", default="دبیرستان نمونه دولتی", help="School name")
    p_comp.add_argument("--teacher", default="دبیر محترم", help="Teacher name")
    p_comp.add_argument("--out-dir", help="Output directory")
    p_comp.set_defaults(func=cmd_compose_exam)

    # graph-query
    p_gq = subparsers.add_parser(
        "graph-query", help="Traverse prerequisite knowledge graph and L1 errors"
    )
    p_gq.add_argument(
        "--concept",
        required=True,
        help="Concept Node ID (e.g. g12.l1.grammar.passive_voice)",
    )
    p_gq.set_defaults(func=cmd_graph_query)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
