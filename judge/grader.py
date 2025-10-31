import time
from problems.models import TestCase
from .run_code import run_program

def compare_output(user_out, expected_out):
    u = [x.rstrip() for x in (user_out or "").split("\n")]
    e = [x.rstrip() for x in (expected_out or "").split("\n")]
    while u and u[-1] == "": u.pop()
    while e and e[-1] == "": e.pop()
    return u == e

def grade_submission(sub):
    problem = sub.problem
    tests = TestCase.objects.filter(problem=problem).order_by("id")

    total = tests.count()
    passed = 0
    total_time = 0
    debug = {}

    for tc in tests:
        start = time.time()
        out, err, _ = run_program(sub.language, sub.source_code, tc.input_data, time_limit=int(problem.time_limit))
        total_time += time.time() - start

        # handle judge flags
        if out == "Time Limit Exceeded":
            sub.debug_info = f"TLE at test {tc.id}"
            return ("Time Limit Exceeded", total_time, passed, total, debug)

        if out.startswith("Compilation Error"):
            sub.debug_info = out + "\n" + err
            return ("Compilation Error", total_time, passed, total, debug)

        if out.startswith("Runtime Error"):
            sub.debug_info = out + "\n" + err
            return ("Runtime Error", total_time, passed, total, debug)

        if not compare_output(out, tc.expected_output):
            debug = {
                "test_id": tc.id,
                "input": tc.input_data,
                "expected": tc.expected_output,
                "got": out,
                "stderr": err,
            }
            sub.debug_info = str(debug)
            return ("Wrong Answer", total_time, passed, total, debug)

        passed += 1

    sub.debug_info = "All tests passed"
    return ("Accepted", total_time, passed, total, debug)
