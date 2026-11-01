import subprocess
import json
import unittest
import sys

PYTHON = sys.executable

class TestCLI(unittest.TestCase):
    def test_cli_context_output(self):
        out = subprocess.check_output([
            PYTHON, "/home/ubuntu/vision_kb/curriculum_kb.py",
            "context", "--grade", "10", "--lessons", "1,2"
        ], text=True)
        data = json.loads(out)
        self.assertEqual(len(data["lessons"]), 2)
        self.assertIn("vocabulary", data)
        self.assertIn("rubric", data)

    def test_cli_search_output(self):
        out = subprocess.check_output([
            PYTHON, "/home/ubuntu/vision_kb/curriculum_kb.py",
            "search", "--query", "cheetah"
        ], text=True)
        data = json.loads(out)
        self.assertGreaterEqual(len(data["passages"]), 1)

    def test_cli_validate_output(self):
        out = subprocess.check_output([
            PYTHON, "/home/ubuntu/vision_kb/curriculum_kb.py",
            "validate", "--grade", "10", "--max-lesson", "2",
            "--text", "The heart pumps blood through the body."
        ], text=True)
        data = json.loads(out)
        self.assertTrue(data["is_valid"])

    def test_cli_stats_output(self):
        out = subprocess.check_output([
            PYTHON, "/home/ubuntu/vision_kb/curriculum_kb.py",
            "stats"
        ], text=True)
        self.assertIn("Grade", out)
        self.assertIn("Prospect", out)
        self.assertIn("Vision", out)

    def test_cli_audit_output(self):
        out = subprocess.check_output([
            PYTHON, "/home/ubuntu/vision_kb/curriculum_kb.py",
            "audit"
        ], text=True)
        data = json.loads(out)
        self.assertTrue(data["audit_passed"])

    def test_cli_adapt_output(self):
        out = subprocess.check_output([
            PYTHON, "/home/ubuntu/vision_kb/curriculum_kb.py",
            "adapt", "--grade", "7", "--max-lesson", "8",
            "--text", "The physician helped the patient."
        ], text=True)
        data = json.loads(out)
        self.assertFalse(data["is_valid"])
        self.assertIn("physician", data["word_diagnostics"])

    def test_cli_blueprint_output(self):
        out = subprocess.check_output([
            PYTHON, "/home/ubuntu/vision_kb/curriculum_kb.py",
            "blueprint", "--grade", "9", "--term", "1"
        ], text=True)
        data = json.loads(out)
        self.assertEqual(data["grade"], 9)
        self.assertEqual(data["term"], 1)
        self.assertIn("tts_template", data)

if __name__ == "__main__":
    unittest.main()
