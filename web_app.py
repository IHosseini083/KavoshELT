#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Deque, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from sqlalchemy import select

from advisor import analyze_and_advise
from ai_generator import VOICE_CATALOG, generate_exam_package_with_ai
from models import Lesson, Passage, session_scope
from schema import init_db
from seed_all_grades import seed_curriculum

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "curriculum.db")
TEMPLATE_PATH = os.path.join(BASE_DIR, "templates", "index.html")
FONTS_DIR = os.path.join(BASE_DIR, "assets", "fonts")

MAX_TEXT_LENGTH = 10000

GRAMMAR_REASONS_FA: Dict[str, str] = {
    "present_perfect": "ساختار ماضی نقلی (Present Perfect) در پایه یازدهم (کتاب Vision 2، درس ۱) تدریس می‌شود و برای این پایه خارج از سرفصل است.",
    "past_progressive": "ساختار گذشته استمراری (Past Progressive) در پایه دهم (کتاب Vision 1، درس ۳) معرفی می‌شود و پیش از آن مجاز نیست.",
    "passive_voice": "ساختار مجهول (Passive Voice) در پایه دوازدهم (کتاب Vision 3، درس ۱) تدریس می‌شود و برای این پایه خارج از سرفصل است.",
    "conditional_type_2": "جملات شرطی نوع دوم (Conditional Type 2) در پایه دوازدهم (کتاب Vision 3، درس ۲) معرفی می‌شود.",
}

BOOK_NAMES_FA: Dict[int, str] = {
    7: "پراسپکت ۱ (پایه هفتم)",
    8: "پراسپکت ۲ (پایه هشتم)",
    9: "پراسپکت ۳ (پایه نهم)",
    10: "ویژن ۱ (پایه دهم)",
    11: "ویژن ۲ (پایه یازدهم)",
    12: "ویژن ۳ (پایه دوازدهم)",
}


def ensure_db() -> str:
    if not os.path.exists(DB_PATH):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        init_db(DB_PATH)
        seed_curriculum(DB_PATH)
    return DB_PATH


class RateLimiter:
    # ponytail: in-memory per-IP deque; upgrade to Redis if scaled to multi-worker processes.
    def __init__(self, max_requests: int = 30, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, ip: str) -> bool:
        now = time.monotonic()
        q = self._hits[ip]
        while q and (now - q[0]) > self.window_seconds:
            q.popleft()
        if len(q) >= self.max_requests:
            return False
        q.append(now)
        return True


GLOBAL_LIMITER = RateLimiter(max_requests=30, window_seconds=60)


def render_index_html() -> str:
    if not os.path.exists(TEMPLATE_PATH):
        return "<!DOCTYPE html><html lang='fa' dir='rtl'><head><meta charset='utf-8'><title>Vision Validator</title></head><body>در حال بارگذاری...</body></html>"
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def handle_api_request(
    method: str,
    path: str,
    payload: Optional[Dict[str, Any]],
    client_ip: str,
    limiter: Optional[RateLimiter] = None,
) -> Tuple[int, Dict[str, Any]]:
    ensure_db()
    active_limiter = limiter or GLOBAL_LIMITER

    if method == "GET" and path == "/api/health":
        return 200, {"status": "ok", "grades": 6, "lessons": 31}

    if method == "GET" and path == "/api/voices":
        return 200, {"voices": list(VOICE_CATALOG.values())}

    if method == "GET" and path == "/api/lessons":
        with session_scope(DB_PATH) as session:
            lessons = list(
                session.scalars(select(Lesson).order_by(Lesson.grade.asc(), Lesson.lesson_num.asc())).all()
            )
            passages = list(
                session.scalars(select(Passage).order_by(Passage.grade.asc(), Passage.lesson_num.asc())).all()
            )

        by_grade: Dict[int, Dict[str, Any]] = {}
        for l_row in lessons:
            g = l_row.grade
            if g not in by_grade:
                by_grade[g] = {
                    "grade": g,
                    "book_fa": BOOK_NAMES_FA.get(g, f"پایه {g}"),
                    "lessons": [],
                    "samples": [],
                }
            by_grade[g]["lessons"].append(
                {
                    "lesson_num": l_row.lesson_num,
                    "title": l_row.title,
                    "theme": l_row.theme,
                }
            )
        for p_row in passages:
            if p_row.grade in by_grade:
                by_grade[p_row.grade]["samples"].append(
                    {
                        "lesson_num": p_row.lesson_num,
                        "title": p_row.title,
                        "content": p_row.content,
                    }
                )
        return 200, {"grades": list(by_grade.values())}

    if method == "POST" and path == "/api/analyze":
        if not active_limiter.allow(client_ip):
            return 429, {"error": "تعداد درخواست‌های شما بیش از حد مجاز است. لطفاً یک دقیقه صبر کنید."}

        if not isinstance(payload, dict):
            return 400, {"error": "فرمت درخواست نامعتبر است."}

        raw_text = str(payload.get("text", "")).strip()
        if not raw_text:
            return 400, {"error": "متن ورودی خالی است. یک متن انگلیسی وارد کنید."}
        if len(raw_text) > MAX_TEXT_LENGTH:
            return 413, {"error": "طول متن بیش از حد مجاز (۱۰٬۰۰۰ کاراکتر) است."}

        try:
            grade = int(payload.get("grade", 10))
            max_lesson = int(payload.get("max_lesson", 2))
        except (ValueError, TypeError):
            return 400, {"error": "پایه یا شماره درس نامعتبر است."}

        if grade not in range(7, 13) or max_lesson not in range(1, 9):
            return 400, {"error": "پایه تحصیلی باید بین ۷ تا ۱۲ باشد."}

        result = analyze_and_advise(DB_PATH, max_grade=grade, max_lesson=max_lesson, text=raw_text)
        word_count = max(1, int(result.get("word_count", 0)))
        out_count = len(result.get("out_of_syllabus_words", []))
        in_count = max(0, word_count - out_count)
        result["coverage_ratio"] = (
            round((in_count / word_count) * 100, 1) if result.get("word_count", 0) > 0 else 100.0
        )

        for g_hit in result.get("forbidden_grammar_hits", []):
            g_type = g_hit.get("type", "")
            g_hit["reason_fa"] = GRAMMAR_REASONS_FA.get(g_type, g_hit.get("reason", ""))

        return 200, result

    if method == "POST" and path == "/api/generate-exam":
        if not active_limiter.allow(client_ip):
            return 429, {"error": "تعداد درخواست‌های شما بیش از حد مجاز است. لطفاً یک دقیقه صبر کنید."}

        if not isinstance(payload, dict):
            return 400, {"error": "فرمت درخواست نامعتبر است."}

        try:
            grade = int(payload.get("grade", 10))
            lesson_num = int(payload.get("lesson_num", 1))
        except (ValueError, TypeError):
            return 400, {"error": "پایه یا شماره درس نامعتبر است."}

        exam_type = str(payload.get("exam_type", "Listening"))
        school_name = str(payload.get("school_name", "دبیرستان نمونه دولتی"))
        teacher_name = str(payload.get("teacher_name", "دبیر محترم"))
        voice1 = str(payload.get("voice1", "fola"))
        voice2 = str(payload.get("voice2", "rami"))
        speed_wpm = int(payload.get("speed_wpm", 130))

        result = generate_exam_package_with_ai(
            grade=grade,
            lesson_num=lesson_num,
            exam_type=exam_type,
            school_name=school_name,
            teacher_name=teacher_name,
            voice1=voice1,
            voice2=voice2,
            speed_wpm=speed_wpm,
        )
        return 200, result

    return 404, {"error": "مسیر مورد نظر یافت نشد."}


class VisionRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _client_ip(self) -> str:
        forwarded = self.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return self.client_address[0]

    def _send_json(self, status: int, data: Dict[str, Any]) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            html_bytes = render_index_html().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html_bytes)))
            self.end_headers()
            self.wfile.write(html_bytes)
            return

        if parsed.path in ("/fonts/Vazirmatn-Regular.ttf", "/fonts/Vazirmatn-Bold.ttf"):
            fname = os.path.basename(parsed.path)
            fpath = os.path.join(FONTS_DIR, fname)
            if os.path.exists(fpath):
                with open(fpath, "rb") as f:
                    font_bytes = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "font/ttf")
                self.send_header("Cache-Control", "public, max-age=31536000, immutable")
                self.send_header("Content-Length", str(len(font_bytes)))
                self.end_headers()
                self.wfile.write(font_bytes)
                return

        if parsed.path.startswith("/api/voice-preview/"):
            fname = os.path.basename(parsed.path)
            previews_dir = os.path.join(BASE_DIR, "assets", "audio_previews")
            fpath = os.path.join(previews_dir, fname)
            if os.path.exists(fpath) and fname.endswith((".mp3", ".wav")):
                with open(fpath, "rb") as f:
                    audio_bytes = f.read()
                mime = "audio/mpeg" if fname.endswith(".mp3") else "audio/wav"
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(audio_bytes)))
                self.end_headers()
                self.wfile.write(audio_bytes)
                return

        if parsed.path.startswith("/api/download/"):
            parts = parsed.path.strip("/").split("/")
            if len(parts) == 4 and parts[0] == "api" and parts[1] == "download":
                sess_id, fname = parts[2], parts[3]
                fpath = os.path.join(BASE_DIR, "exports", "generated", sess_id, fname)
                if os.path.exists(fpath):
                    with open(fpath, "rb") as f:
                        file_bytes = f.read()
                    mime = "application/octet-stream"
                    if fname.endswith(".docx"):
                        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    elif fname.endswith(".pdf"):
                        mime = "application/pdf"
                    elif fname.endswith(".html"):
                        mime = "text/html; charset=utf-8"
                    elif fname.endswith(".mp3"):
                        mime = "audio/mpeg"
                    self.send_response(200)
                    self.send_header("Content-Type", mime)
                    self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
                    self.send_header("Content-Length", str(len(file_bytes)))
                    self.end_headers()
                    self.wfile.write(file_bytes)
                    return

        status, body = handle_api_request("GET", parsed.path, None, self._client_ip())
        self._send_json(status, body)

    do_HEAD = do_GET

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        if length > 65536:
            self._send_json(413, {"error": "حجم درخواست بیش از حد مجاز است."})
            return
        raw_body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception:
            self._send_json(400, {"error": "ساختار JSON نامعتبر است."})
            return

        status, body = handle_api_request("POST", parsed.path, payload, self._client_ip())
        self._send_json(status, body)


def run_server(host: str = "127.0.0.1", port: int = 8090) -> None:
    ensure_db()
    server = ThreadingHTTPServer((host, port), VisionRequestHandler)
    print(f"[OK] Vision Web Server listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    port_val = int(os.environ.get("PORT", "8090"))
    host_val = os.environ.get("HOST", "127.0.0.1")
    run_server(host=host_val, port=port_val)
