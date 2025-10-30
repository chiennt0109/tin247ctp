# path: judge/grader.py
import time
from problems.models import TestCase
from .run_code import run_program

def normalize(text):
    if text is None:
        return ""
    return text.replace("\r\n", "\n").rstrip()

def compare_output(user_out, expected_out):
    u = [line.rstrip() for line in normalize(user_out).split("\n")]
    e = [line.rstrip() for line in normalize(expected_out).split("\n")]

    # Bỏ dòng trống cuối nếu có
    while u and u[-1] == "":
        u.pop()
    while e and e[-1] == "":
        e.pop()

    if len(u) != len(e):
        return False

    for a, b in zip(u, e):
        if a != b:
            return False

    return True

def grade_submission(submission):
    problem = submission.problem
    tests = TestCase.objects.filter(problem=problem).order_by("id")

    total = tests.count()
    passed = 0
    total_time = 0
    debug = {}

    for tc in tests:
        start = time.time()
        out, err = run_program(
            submission.language,
            submission.source_code,
            tc.input_data,
            time_limit=max(int(problem.time_limit), 1)
        )
        elapsed = time.time() - start
        total_time += elapsed

        if out.startswith("Compilation Error"):
            return ("Compilation Error", total_time, passed, total, {"tc": tc.id, "err": err})

        if out.startswith("Runtime Error"):
            return ("Runtime Error", total_time, passed, total, {"tc": tc.id, "err": err})

        if out == "Time Limit Exceeded":
            return ("Time Limit Exceeded", total_time, passed, total, {"tc": tc.id})

        if out.startswith("API Error"):
            return ("Runtime Error", total_time, passed, total, {"tc": tc.id, "err": out})

        if not compare_output(out, tc.expected_output):
            debug = {
                "tc": tc.id,
                "input": tc.input_data,
                "expected": tc.expected_output,
                "out": out,
                "err": err
            }
            return ("Wrong Answer", total_time, passed, total, debug)

        passed += 1

    return ("Accepted", total_time, passed, total, debug)
