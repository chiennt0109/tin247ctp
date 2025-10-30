# path: judge/grader.py
import time
from problems.models import TestCase
from .run_code import run_program


def normalize(text):
    if text is None:
        return ""
    return text.replace("\r\n", "\n").strip()


def compare_output(user_out, expected_out):
    """So sánh từng dòng, bỏ dòng trống và \r"""
    u_lines = [line.rstrip() for line in normalize(user_out).split("\n") if line.strip() != ""]
    e_lines = [line.rstrip() for line in normalize(expected_out).split("\n") if line.strip() != ""]
    return u_lines == e_lines


def grade_submission(submission):
    """
    Chấm từng test case trong DB.
    Trả về (verdict, total_time, passed, total, debug_info)
    """
    problem = submission.problem
    tests = TestCase.objects.filter(problem=problem).order_by("id")

    total = tests.count()
    passed = 0
    total_time = 0.0
    debug_info = ""

    if total == 0:
        return ("No Testcases", 0, 0, 0, "⚠️ Problem has no testcases")

    for tc in tests:
        start_time = time.time()
        out, err = run_program(submission.language, submission.source_code, tc.input_data)
        elapsed = time.time() - start_time
        total_time += elapsed

        # Phát hiện lỗi biên dịch hoặc runtime
        if out.startswith("Compilation Error"):
            debug_info = f"[Test {tc.id}] Compilation Error:\n{err}"
            return ("Compilation Error", total_time, passed, total, debug_info)
        if out.startswith("Runtime Error"):
            debug_info = f"[Test {tc.id}] Runtime Error:\n{err}"
            return ("Runtime Error", total_time, passed, total, debug_info)
        if out.startswith("Time Limit Exceeded"):
            debug_info = f"[Test {tc.id}] Time Limit Exceeded"
            return ("Time Limit Exceeded", total_time, passed, total, debug_info)
        if out.startswith("API Error"):
            debug_info = f"[Test {tc.id}] API Error → {out}"
            return ("Runtime Error", total_time, passed, total, debug_info)

        # So sánh kết quả
        if not compare_output(out, tc.expected_output):
            debug_info = (
                f"\n❌ [Test {tc.id}] WRONG ANSWER\n"
                f"Input:\n{tc.input_data}\n"
                f"Expected:\n{tc.expected_output}\n"
                f"Got:\n{out}\n"
                f"Stderr:\n{err}\n"
            )
            return ("Wrong Answer", total_time, passed, total, debug_info)

        passed += 1

    debug_info = f"✅ Passed all {passed}/{total} tests"
    return ("Accepted", total_time, passed, total, debug_info)
