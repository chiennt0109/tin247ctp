# path: submissions/grader.py
from problems.models import TestCase
from .run_code import run_program
import time

def normalize(s: str) -> str:
    """
    Chuẩn hóa chuỗi output:
    - Replace CRLF -> LF
    - Strip trailing space
    - So sánh theo từng dòng
    """
    if s is None:
        return ""
    return s.replace("\r\n", "\n").rstrip()

def compare_output(user_out: str, expected_out: str) -> bool:
    """
    So sánh output theo từng dòng, bỏ khoảng trắng cuối dòng.
    Không cắt dòng bằng '...' nên bạn xem toàn bộ output thật.
    """
    u = normalize(user_out).split("\n")
    e = normalize(expected_out).split("\n")

    if len(u) != len(e):
        return False

    for a, b in zip(u, e):
        if a.rstrip() != b.rstrip():
            return False

    return True

def grade_submission(submission):
    problem = submission.problem
    testcases = TestCase.objects.filter(problem=problem).order_by("id")

    total_time = 0.0
    passed = 0
    total = testcases.count()

    for tc in testcases:
        start = time.time()
        out, err = run_program(
            submission.language,
            submission.source_code,
            tc.input_data,
            time_limit=problem.time_limit
        )
        elapsed = max(0.0, time.time() - start)
        total_time += elapsed

        # ❌ Biên dịch / Runtime
        if out.startswith("Compilation Error"):
            return ("Compilation Error", total_time, passed, total)

        if out.startswith("Runtime Error"):
            return ("Runtime Error", total_time, passed, total)

        if out == "Time Limit Exceeded":
            return ("Time Limit Exceeded", total_time, passed, total)

        # ❌ Sai output
        if not compare_output(out, tc.expected_output):
            return ("Wrong Answer", total_time, passed, total)

        passed += 1

    # ✅ Passed all tests
    return ("Accepted", total_time, passed, total)
