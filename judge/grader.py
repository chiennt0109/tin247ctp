from problems.models import TestCase
from .run_code import run_program
import time


def normalize(s: str) -> str:
    """Chuẩn hóa output để so sánh công bằng"""
    return (s or "").strip().replace('\r\n', '\n').rstrip()


def grade_submission(submission):
    """
    Chấm từng test, tính thời gian, đếm số test đúng/sai.
    Trả về (verdict, total_time, passed, failed)
    """
    problem = submission.problem
    testcases = TestCase.objects.filter(problem=problem)
    total_time = 0.0
    passed, failed = 0, 0

    if not testcases.exists():
        return ("No Test Cases", 0.0, 0, 0)

    for i, tc in enumerate(testcases, start=1):
        start = time.time()
        out, _ = run_program(submission.language, submission.source_code, tc.input_data, time_limit=problem.time_limit)
        elapsed = max(0.0, time.time() - start)
        total_time += elapsed

        # Kiểm tra lỗi biên dịch/chạy
        if any(out.startswith(err) for err in ["Time Limit", "Compilation", "Runtime", "API Error", "Internal Error"]):
            failed += 1
            return (out, total_time, passed, failed)

        # So sánh kết quả
        if normalize(out) == normalize(tc.expected_output):
            passed += 1
        else:
            failed += 1

    verdict = "Accepted" if failed == 0 else f"Passed {passed}/{passed+failed}"
    return (verdict, total_time, passed, failed)
