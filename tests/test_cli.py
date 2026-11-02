from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest

PYTHON = sys.executable
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestCLI(unittest.TestCase):
    def _run_cli(self, *args: str) -> str:
        return subprocess.check_output(
            [PYTHON, "-m", "kavosh", *args],
            cwd=ROOT_DIR,
            text=True,
        )

    def test_cli_context_output(self) -> None:
        out = self._run_cli("context", "--grade", "10", "--lessons", "1,2")
        data = json.loads(out)
        self.assertEqual(len(data["lessons"]), 2)
        self.assertIn("vocabulary", data)
        self.assertIn("rubric", data)

    def test_cli_search_output(self) -> None:
        out = self._run_cli("search", "--query", "cheetah")
        data = json.loads(out)
        self.assertGreaterEqual(len(data["passages"]), 1)

    def test_cli_validate_output(self) -> None:
        out = self._run_cli(
            "validate",
            "--grade",
            "10",
            "--max-lesson",
            "2",
            "--text",
            "The heart pumps blood through the body.",
        )
        data = json.loads(out)
        self.assertTrue(data["is_valid"])

    def test_cli_stats_output(self) -> None:
        out = self._run_cli("stats")
        self.assertIn("Grade", out)
        self.assertIn("Prospect", out)
        self.assertIn("Vision", out)

    def test_cli_audit_output(self) -> None:
        out = self._run_cli("audit")
        data = json.loads(out)
        self.assertTrue(data["audit_passed"])

    def test_cli_adapt_output(self) -> None:
        out = self._run_cli(
            "adapt",
            "--grade",
            "7",
            "--max-lesson",
            "8",
            "--text",
            "The physician helped the patient.",
        )
        data = json.loads(out)
        self.assertFalse(data["is_valid"])
        self.assertIn("physician", data["word_diagnostics"])

    def test_cli_blueprint_output(self) -> None:
        out = self._run_cli("blueprint", "--grade", "9", "--term", "1")
        data = json.loads(out)
        self.assertEqual(data["grade"], 9)
        self.assertEqual(data["term"], 1)
        self.assertIn("tts_template", data)

    def test_cli_graph_query_output(self) -> None:
        out = self._run_cli("graph-query", "--concept", "g12.l1.grammar.passive_voice")
        data = json.loads(out)
        self.assertEqual(data["concept"]["id"], "g12.l1.grammar.passive_voice")
        self.assertGreaterEqual(len(data["prerequisites"]), 2)


if __name__ == "__main__":
    unittest.main()
