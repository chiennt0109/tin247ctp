# path: judge/grader.py
import time
import re
from problems.models import TestCase
from .run_code import run_program

# --- Sanitizers --------------------------------------------------------------

# Chuẩn hóa ký tự xuống dòng, loại BOM/zero-width, thay NBSP, gom whitespace dị thường.
_ZWS = "\u200b\u200c\u200d\u2060\ufeff"
_ZWS_RE = re.compile(f"[{re.escape(_ZWS)}]")

def _normalize_newlines(text: str) -> str:
    # CRLF/CR -> LF
    return text.replace("\r\n", "\n").replace("\r", "\n")

def _sanitize_text(text: str) -> str:
    if text is None:
        return ""
    # Bước 1: về str chuẩn + chuẩn hóa newline
    s = _normalize_newlines(str(text))
    # Bước 2: bỏ BOM đầu chuỗi nếu có
    if s.startswith("\ufeff"):
        s = s.lstrip("\ufeff")
    # Bước 3: bỏ zero width chars
    s = _ZWS_RE.sub("", s)
    # Bước 4: đổi NBSP thành space
    s = s.replace("\xa0", " ")
    # Không strip toàn cục: giữ nguyên spaces nội dung, chỉ rstrip từng dòng khi so sánh
    return s

def _lines_for_compare(text: str):
    s = _sanitize_text(text)
    lines = s.split("\n")
    # rstrip từng dòng để bỏ space cuối dòng; bỏ các dòng trống đuôi
    lines = [ln.rstrip() for ln in lines]
    while lines and lines[-1] == "":
        lines.pop()
    return lines

def normalize(text: str) -> str:
    # Giữ lại cho tương thích cũ (nếu nơi khác còn dùng)
    return _sanitize_text(text).rstrip()

def compare_output(user_out: str, expected_out: str) -> bool:
    u = _lines_for_compare(user_out)
    e = _lines_for_compare(expected_out)
    if len(u) != len(e):
        return False
    for a, b in zip(u, e):
        if a != b:
            return False
    return True

def _show_invisibles_snippet(s: str, limit=120) -> str:
    """Hiển thị đoạn đầu với escape để nhìn thấy ký tự ẩn + mã hex."""
    snippet = _sanitize_text(s)[:limit]
    # escape để nhìn rõ \n, \t...
    esc = snippet.encode("unicode_escape").decode("ascii")
    hexs = " ".join(f"{ord(ch):02X}" for ch in snippet)
    return f"{esc}\nHEX: {hexs}"

# --- Grader ------------------------------------------------------------------

def grade_submission(submission):
    problem = submission.problem
    tests = TestCase.objects.filter(problem=problem).order_by("id")

    total = tests.count()
    passed = 0
    total_time = 0.0
    debug = {}

    for tc in tests:
        # Sanitize input và expected trước khi dùng
        clean_input = _sanitize_text(tc.input_data)
        clean_expected = _sanitize_text(tc.expected_output)

        start = time.time()
        out, err = run_program(
            submission.language,
            submission.source_code,
            clean_input,
            time_limit=max(int(problem.time_limit), 1)
        )
        elapsed = time.time() - start
        total_time += elapsed

        # Chuẩn hóa out/err cho nhánh lỗi
        out_s = _sanitize_text(out)
        err_s = _sanitize_text(err)

        if out_s.startswith("Compilation Error"):
            return ("Compilation Error", total_time, passed, total, {"tc": tc.id, "stderr": err_s})

        if out_s.startswith("Runtime Error"):
            return ("Runtime Error", total_time, passed, total, {"tc": tc.id, "stderr": err_s})

        if out_s == "Time Limit Exceeded":
            return ("Time Limit Exceeded", total_time, passed, total, {"tc": tc.id})

        if out_s.startswith("API Error") or out_s.startswith("Internal Error"):
            return ("Runtime Error", total_time, passed, total, {"tc": tc.id, "stderr": out_s})

        # So sánh
        if not compare_output(out_s, clean_expected):
            debug = {
                "tc": tc.id,
                "input_preview": _show_invisibles_snippet(clean_input),
                "expected_preview": _show_invisibles_snippet(clean_expected),
                "got_preview": _show_invisibles_snippet(out_s),
                "stderr_preview": _show_invisibles_snippet(err_s),
                "note": "Ký tự ẩn đã được loại khỏi so sánh; xem ESC/HEX để phát hiện khoảng trắng lạ."
            }
            return ("Wrong Answer", total_time, passed, total, debug)

        passed += 1

    return ("Accepted", total_time, passed, total, debug)
