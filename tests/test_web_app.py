from __future__ import annotations

import json
import unittest
from typing import Any, Dict

from web_app import RateLimiter, handle_api_request, render_index_html


class TestWebApp(unittest.TestCase):
    def test_health_endpoint(self) -> None:
        status, body = handle_api_request("GET", "/api/health", None, "127.0.0.1")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["grades"], 6)
        self.assertEqual(body["lessons"], 31)

    def test_lessons_endpoint(self) -> None:
        status, body = handle_api_request("GET", "/api/lessons", None, "127.0.0.1")
        self.assertEqual(status, 200)
        self.assertEqual(len(body["grades"]), 6)
        self.assertEqual(body["grades"][0]["grade"], 7)

    def test_analyze_valid_and_out_of_syllabus(self) -> None:
        payload = {
            "grade": 7,
            "max_lesson": 8,
            "text": "The physician helped the patient.",
        }
        status, body = handle_api_request("POST", "/api/analyze", payload, "127.0.0.1")
        self.assertEqual(status, 200)
        self.assertFalse(body["is_valid"])
        self.assertIn("physician", body["out_of_syllabus_words"])
        diag = body["word_diagnostics"]["physician"]
        self.assertEqual(diag["taught_in_grade"], 10)
        self.assertIn("doctor", diag["in_syllabus_alternatives"])
        self.assertIn("coverage_ratio", body)

    def test_analyze_empty_and_oversized_input(self) -> None:
        status_empty, _ = handle_api_request(
            "POST", "/api/analyze", {"grade": 10, "max_lesson": 2, "text": "   "}, "127.0.0.1"
        )
        self.assertEqual(status_empty, 400)

        status_large, _ = handle_api_request(
            "POST", "/api/analyze", {"grade": 10, "max_lesson": 2, "text": "a " * 6000}, "127.0.0.1"
        )
        self.assertEqual(status_large, 413)

    def test_rate_limiter(self) -> None:
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        self.assertTrue(limiter.allow("192.0.2.1"))
        self.assertTrue(limiter.allow("192.0.2.1"))
        self.assertTrue(limiter.allow("192.0.2.1"))
        self.assertFalse(limiter.allow("192.0.2.1"))

    def test_index_html_antislop_compliance(self) -> None:
        html_str = render_index_html()
        self.assertIn('<html lang="fa" dir="rtl">', html_str)
        self.assertIn('role="radiogroup"', html_str)
        self.assertNotIn("—", html_str)


if __name__ == "__main__":
    unittest.main()
