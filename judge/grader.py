# path: judge/grader.py
import time
from problems.models import TestCase
from .run_code import run_program

def normalize(t):
    if t is None: return ""
    return t.replace("\r", "").rstrip()

def same(a, b):
    ua = normalize(a).split("\n")
    ub = normalize(b).split("\n")
    ua = [x.rstrip() for x in ua if x.strip() != "" or True]
    ub = [x.rstrip() for x in ub if x.strip() != "" or True]
    return ua == ub

def grade_submission(sub):
    problem = sub.problem
    tests = TestCase.objects.filter(problem=problem)
    total = tests.count()
    passed = 0
    total_time = 0
    debug = {}

    for tc in tests:
        start = time.time()

        result = run_program(sub.language, sub.source_code, tc.input_data, time_limit=problem.time_limit)

        if isinstance(result, tuple):
            out = result[0]
            err = result[1] if len(result) > 1 else ""
        else:
            out = str(result)
            err = ""

        total_time += time.time() - start

        # classification
        if out.startswith("Compilation Error"):
            return ("Compilation Error", total_time, passed, total, {"test": tc.id, "err": err})

        if out.startswith("Runtime Error"):
            return ("Runtime Error", total_time, passed, total, {"test": tc.id, "err": err})

        if out.strip() == "Time Limit Exceeded":
            return ("Time Limit Exceeded", total_time, passed, total, {"test": tc.id})

        if not same(out, tc.expected_output):
            debug = {
                "test": tc.id,
                "input": tc.input_data,
                "expected": tc.expected_output,
                "got": out,
                "stderr": err
            }
            return ("Wrong Answer", total_time, passed, total, debug)

        passed += 1

    return ("Accepted", total_time, passed, total, debug)
