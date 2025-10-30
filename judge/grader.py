import time
from problems.models import TestCase
from .run_code import run_program

def norm(x):
    return (x or "").replace("\r\n", "\n").rstrip()

def cmp(a, b):
    a = [i.rstrip() for i in norm(a).split("\n") if i.strip() != ""]
    b = [i.rstrip() for i in norm(b).split("\n") if i.strip() != ""]
    return a == b

def grade_submission(sub):
    prob = sub.problem
    tests = TestCase.objects.filter(problem=prob).order_by("id")

    total = tests.count()
    passed = 0
    total_time = 0
    debug = []

    for tc in tests:
        t0 = time.time()
        out, err = run_program(
            sub.language, sub.source_code, tc.input_data,
            time_limit=max(int(prob.time_limit), 1)
        )
        total_time += time.time() - t0

        if out.startswith("Runtime Error") or out.startswith("Internal Error"):
            return ("Runtime Error", total_time, passed, total, {
                "tc": tc.id, "input": tc.input_data,
                "err": out
            })

        if out == "Time Limit Exceeded":
            return ("Time Limit Exceeded", total_time, passed, total, {"tc": tc.id})

        if not cmp(out, tc.expected_output):
            return ("Wrong Answer", total_time, passed, total, {
                "tc": tc.id,
                "input": tc.input_data,
                "expected": tc.expected_output,
                "output": out
            })

        passed += 1

    return ("Accepted", total_time, passed, total, {})
