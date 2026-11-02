"""Model Context Protocol server exposing the KavoshELT curriculum engine.

Run with ``kavosh-mcp`` (stdio transport).  Environment: ``KAVOSH_DB`` selects a
custom SQLite database; otherwise the bundled/cached curriculum database is used.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from importlib import import_module
from typing import Any

from kavosh import __version__
from kavosh.service import KavoshService, get_service


def _server_class() -> Any:
    """``FastMCP`` on mcp 1.x, ``MCPServer`` on mcp 2.x (identical decorator API)."""
    try:
        return import_module("mcp.server.fastmcp").FastMCP
    except (ImportError, AttributeError):
        return import_module("mcp.server.mcpserver").MCPServer


INSTRUCTIONS = (
    "KavoshELT knows the Iranian secondary English curriculum (Prospect 1-3 = "
    "grades 7-9, Vision 1-3 = grades 10-12) and the 27 national grade-12 exams. "
    "Use validate_text before showing text to students, suggest_synonyms to repair "
    "out-of-bounds words, get_lesson_bounds / the curriculum:// resources for ground "
    "truth, and retrieve_exam_questions / get_l1_interference to design exam items."
)


def create_server(db_path: str | None = None) -> Any:
    """Build the MCP server; the database is opened lazily on the first call."""
    server: Any = _server_class()("kavosh-elt", instructions=INSTRUCTIONS)

    def svc() -> KavoshService:
        return get_service(db_path)

    def validate_text(
        text: str, target_grade: int, target_lesson: int | None = None
    ) -> dict[str, Any]:
        """Check English text against the cumulative vocabulary and grammar taught
        up to ``target_grade`` / ``target_lesson`` (whole grade when omitted).

        Returns ``{is_valid, out_of_bounds_tokens, violations}``.
        """
        return svc().validate_text(text, target_grade, target_lesson)

    def suggest_synonyms(text: str, target_grade: int) -> dict[str, Any]:
        """For every out-of-bounds token in ``text`` return ranked in-syllabus
        replacements that students know by the end of ``target_grade``."""
        return svc().suggest_synonyms(text, target_grade)

    def get_lesson_bounds(grade: int, lesson: int) -> dict[str, Any]:
        """Exact lexical and grammatical boundary of one lesson: vocabulary,
        grammar formulas, communicative functions, and forbidden structures."""
        return svc().get_lesson_bounds(grade, lesson)

    def search_curriculum(
        query: str, grade: int | None = None, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Hybrid (semantic + full-text) search over textbook readings and
        conversations, optionally restricted to one grade."""
        return svc().search_curriculum(query, grade, limit)

    def retrieve_exam_questions(
        section: str | None = None, topic: str | None = None, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Authentic items from the 27 national grade-12 exams (1397-1405) with
        answer keys, rubrics and distractor rationales. ``section`` is one of
        vocabulary, grammar, writing, cloze, reading."""
        return svc().retrieve_exam_questions(section, topic, limit)

    def get_l1_interference(category: str | None = None) -> list[dict[str, Any]]:
        """Persian-to-English negative-transfer patterns (e.g. omitted passive
        auxiliaries) for designing plausible distractors. ``category`` filters by
        concept category (grammar, vocabulary, writing, reading) or keyword."""
        return svc().get_l1_interference(category)

    def lesson_resource(grade: str, lesson: str) -> str:
        """Canonical conversation, reading, vocabulary and grammar of one lesson."""
        return svc().lesson_markdown(int(grade), int(lesson))

    def curriculum_index() -> str:
        """Index of all lesson resources."""
        return svc().curriculum_index_markdown()

    for tool in (
        validate_text,
        suggest_synonyms,
        get_lesson_bounds,
        search_curriculum,
        retrieve_exam_questions,
        get_l1_interference,
    ):
        server.tool()(tool)
    server.resource(
        "curriculum://grade/{grade}/lesson/{lesson}", mime_type="text/markdown"
    )(lesson_resource)
    server.resource("curriculum://index", mime_type="text/markdown")(curriculum_index)
    return server


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="kavosh-mcp", description="KavoshELT MCP server (stdio transport)"
    )
    parser.add_argument("--db", default=None, help="Custom SQLite database path")
    parser.add_argument(
        "--version", action="version", version=f"kavosh-mcp {__version__}"
    )
    args = parser.parse_args(argv)
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    create_server(args.db).run(transport="stdio")


if __name__ == "__main__":
    main()
