import time
from problems.models import TestCase
from .run_code import run_program

def _normalize(text: str) -> str:
    if text is None:
        return ""
    # Chuẩn hoá: CRLF -> LF, bỏ khoảng trắng cuối dòng & dòng trống cuối
    text = text.replace("\r\n", "\n")
    lines = [ln.rstrip() for ln in text.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)

def _compare_output(user_out: str, expected_out: str) -> bool:
    u = _normalize(user_out).split("\n")
    e = _normalize(expected_out).split("\n")
    if len(u) != len(e):
        return False
    for a, b in zip(u, e):
        if a != b:
            return False
    return True

def grade_submission(submission):
    """
    Trả về đúng định dạng 4 phần tử:
        (verdict: str, exec_time: float, passed: int, total: int)

    -> Giữ tương thích với submissions/views.py hiện tại của bạn.
    """
    problem = submission.problem
    tests = TestCase.objects.filter(problem=problem).order_by("id")

    total = tests.count()
    passed = 0
    total_time = 0.0

    for tc in tests:
        start = time.time()
        out, err = run_program(
            submission.language,
            submission.source_code,
            tc.input_data,
            time_limit=max(int(problem.time_limit), 1)
        )
        elapsed = max(0.0, time.time() - start)
        total_time += elapsed

        # Phân loại lỗi
        if isinstance(out, str) and out.startswith("Compilation Error"):
            return ("Compilation Error", total_time, passed, total)
        if isinstance(out, str) and out.startswith("Runtime Error"):
            return ("Runtime Error", total_time, passed, total)
        if out == "Time Limit Exceeded":
            return ("Time Limit Exceeded", total_time, passed, total)
        if isinstance(out, str) and out.startswith("API Error"):
            return ("Runtime Error", total_time, passed, total)

        # So sánh kết quả
        if not _compare_output(out or "", tc.expected_output or ""):
            return ("Wrong Answer", total_time, passed, total)

        passed += 1

    return ("Accepted", total_time, passed, total)
