"""End-to-end tests of the MCP server over the real stdio transport."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import unittest
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from kavosh.paths import build_database_file

EXPECTED_TOOLS = {
    "validate_text",
    "suggest_synonyms",
    "get_lesson_bounds",
    "search_curriculum",
    "retrieve_exam_questions",
    "get_l1_interference",
}


def _get(obj: Any, *names: str) -> Any:
    """Read an attribute under its camelCase (mcp 1.x) or snake_case (mcp 2.x) name."""
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    raise AttributeError(f"{type(obj).__name__} has none of {names}")


def _payload(result: Any) -> Any:
    """Decode a tool result across SDK versions (structured or text content)."""
    assert not _get(result, "isError", "is_error"), result
    structured = _get(result, "structuredContent", "structured_content")
    if structured is not None:
        if isinstance(structured, dict) and set(structured) == {"result"}:
            return structured["result"]
        return structured
    decoded = [json.loads(c.text) for c in result.content if c.type == "text"]
    return decoded[0] if len(decoded) == 1 else decoded


class TestMcpServerOverStdio(unittest.TestCase):
    tmp: tempfile.TemporaryDirectory[str]
    db_path: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_path = build_database_file(Path(cls.tmp.name) / "curriculum.db")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def _run(self, scenario: Callable[[ClientSession], Awaitable[None]]) -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "kavosh.mcp_server"],
            env={**os.environ, "KAVOSH_DB": str(self.db_path)},
        )

        async def main() -> None:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    await scenario(session)

        asyncio.run(asyncio.wait_for(main(), timeout=120))

    async def _call(
        self, session: ClientSession, name: str, args: dict[str, Any]
    ) -> Any:
        return _payload(await session.call_tool(name, args))

    def test_lists_all_tools_and_resources(self) -> None:
        async def scenario(session: ClientSession) -> None:
            tools = {t.name for t in (await session.list_tools()).tools}
            self.assertTrue(EXPECTED_TOOLS <= tools, tools)
            templates = await session.list_resource_templates()
            uris = {
                _get(t, "uriTemplate", "uri_template")
                for t in _get(templates, "resourceTemplates", "resource_templates")
            }
            self.assertIn("curriculum://grade/{grade}/lesson/{lesson}", uris)

        self._run(scenario)

    def test_validate_text(self) -> None:
        async def scenario(session: ClientSession) -> None:
            ok = await self._call(
                session,
                "validate_text",
                {
                    "text": "The heart pumps blood through the body.",
                    "target_grade": 10,
                    "target_lesson": 2,
                },
            )
            self.assertTrue(ok["is_valid"], ok)
            self.assertEqual(ok["out_of_bounds_tokens"], [])
            self.assertEqual(ok["violations"], [])

            bad = await self._call(
                session,
                "validate_text",
                {
                    "text": "Amir has visited the photosynthesis laboratory.",
                    "target_grade": 9,
                },
            )
            self.assertFalse(bad["is_valid"])
            self.assertIn("photosynthesis", bad["out_of_bounds_tokens"])
            self.assertTrue(any("present_perfect" in v for v in bad["violations"]))

        self._run(scenario)

    def test_validate_text_rejects_bad_grade(self) -> None:
        async def scenario(session: ClientSession) -> None:
            result = await session.call_tool(
                "validate_text", {"text": "Hello", "target_grade": 3}
            )
            self.assertTrue(_get(result, "isError", "is_error"))

        self._run(scenario)

    def test_suggest_synonyms(self) -> None:
        async def scenario(session: ClientSession) -> None:
            res = await self._call(
                session,
                "suggest_synonyms",
                {"text": "The physician helped the patient.", "target_grade": 7},
            )
            self.assertIn("physician", res["out_of_bounds_tokens"])
            words = [s["word"] for s in res["suggestions"]["physician"]]
            self.assertIn("doctor", words)
            self.assertEqual(res["taught_in"]["physician"]["grade"], 10)

        self._run(scenario)

    def test_get_lesson_bounds(self) -> None:
        async def scenario(session: ClientSession) -> None:
            res = await self._call(
                session, "get_lesson_bounds", {"grade": 10, "lesson": 1}
            )
            self.assertEqual(res["title"], "Saving Nature")
            self.assertTrue(res["vocabulary"])
            self.assertTrue(res["grammar_formulas"])
            self.assertIn("forbidden_tenses", res["forbidden_grammar"])
            missing = await session.call_tool(
                "get_lesson_bounds", {"grade": 10, "lesson": 9}
            )
            self.assertTrue(_get(missing, "isError", "is_error"))

        self._run(scenario)

    def test_search_curriculum(self) -> None:
        async def scenario(session: ClientSession) -> None:
            hits = await self._call(
                session, "search_curriculum", {"query": "cheetah", "limit": 3}
            )
            self.assertTrue(1 <= len(hits) <= 3)
            self.assertIn("content", hits[0])
            scoped = await self._call(
                session,
                "search_curriculum",
                {"query": "family", "grade": 7, "limit": 5},
            )
            self.assertTrue(scoped)
            self.assertTrue(all(h["grade"] == 7 for h in scoped))

        self._run(scenario)

    def test_retrieve_exam_questions(self) -> None:
        async def scenario(session: ClientSession) -> None:
            items = await self._call(
                session,
                "retrieve_exam_questions",
                {"section": "grammar", "topic": "passive voice", "limit": 4},
            )
            self.assertTrue(1 <= len(items) <= 4)
            for item in items:
                self.assertEqual(item["section"], "grammar")
                self.assertTrue(item["answer"])
                self.assertIsInstance(item["rubric"], dict)
                self.assertIn("distractor_rationale", item)

        self._run(scenario)

    def test_exam_questions_flag_machine_drafted_distractors(self) -> None:
        async def scenario(session: ClientSession) -> None:
            items = await self._call(
                session,
                "retrieve_exam_questions",
                {"section": "cloze", "topic": "dictionary", "limit": 5},
            )
            self.assertTrue(items)
            for item in items:
                self.assertTrue(item["distractor_rationale"])
                self.assertEqual(item["distractor_status"], "machine_drafted")

        self._run(scenario)

    def test_get_l1_interference(self) -> None:
        async def scenario(session: ClientSession) -> None:
            rows = await self._call(session, "get_l1_interference", {})
            self.assertGreaterEqual(len(rows), 4)
            self.assertIn("incorrect_pattern", rows[0])
            grammar = await self._call(
                session, "get_l1_interference", {"category": "grammar"}
            )
            self.assertTrue(grammar)
            self.assertTrue(all(r["category"] == "grammar" for r in grammar))
            none = await self._call(
                session, "get_l1_interference", {"category": "zzzz"}
            )
            self.assertEqual(none, [])

        self._run(scenario)

    def test_lesson_resource(self) -> None:
        async def scenario(session: ClientSession) -> None:
            res = await session.read_resource("curriculum://grade/10/lesson/1")
            text = "".join(getattr(c, "text", "") for c in res.contents)
            self.assertIn("Saving Nature", text)
            self.assertIn("## Conversation", text)
            self.assertIn("## Reading", text)
            self.assertIn("## Target vocabulary", text)
            self.assertIn("## Grammar summary", text)
            index = await session.read_resource("curriculum://index")
            self.assertIn(
                "curriculum://grade/12/lesson/3",
                "".join(getattr(c, "text", "") for c in index.contents),
            )

        self._run(scenario)


if __name__ == "__main__":
    unittest.main()
