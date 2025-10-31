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

    while u and u[-1] == "": u.pop()
    while e and e[-1] == "": e.pop()

    return u == e

def grade_submission(sub):
    problem = sub.problem
    tests = TestCase.objects.filter(problem=problem).order_by("id")

    total = tests.count()
    passed = 0
    total_time = 0
    debug_info = {}

    for tc in tests:
        start = time.time()
        result = run_program(sub.language, sub.source_code, tc.input_data, time_limit=problem.time_limit)

        # ✅ normalize return type: always tuple (stdout, stderr)
        if isinstance(result, tuple):
            out = result[0] if len(result) > 0 else ""
            err = result[1] if len(result) > 1 else ""
        else:
            out = str(result)
            err = ""

        elapsed = time.time() - start
        total_time += elapsed

        # Standard error detection
        if out.startswith("Compilation Error"):
            return ("Compilation Error", total_time, passed, total, f"TC {tc.id}\n{err}")

        if out.startswith("Runtime Error"):
            return ("Runtime Error", total_time, passed, total, f"TC {tc.id}\n{err}")

        if out.strip() == "Time Limit Exceeded":
            return ("Time Limit Exceeded", total_time, passed, total, f"TC {tc.id}")

        # Wrong answer check
        if not compare_output(out, tc.expected_output):
            debug_info = {
                "test_id": tc.id,
                "input": tc.input_data,
                "expected": tc.expected_output,
                "got": out,
                "stderr": err
            }
            return ("Wrong Answer", total_time, passed, total, debug_info)

        passed += 1

    return ("Accepted", total_time, passed, total, debug_info)
