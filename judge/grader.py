# path: judge/grader.py
import time
from problems.models import TestCase
from .run_code import run_program

def normalize(s):
    return "" if s is None else s.replace("\r\n","\n").rstrip()

def compare(a,b):
    ua = [x.rstrip() for x in normalize(a).split("\n") if x != ""]
    ub = [x.rstrip() for x in normalize(b).split("\n") if x != ""]
    return ua == ub

def grade_submission(sub):
    tests = TestCase.objects.filter(problem=sub.problem).order_by("id")
    passed = 0
    total = tests.count()
    total_time = 0
    debug = ""

    for tc in tests:
        start = time.time()
        out, err = run_program(sub.language, sub.source_code, tc.input_data, time_limit=3)
        total_time += time.time() - start

        if "Error" in out or "not supported" in out:
            return ("Runtime Error", total_time, passed, total, out)

        if not compare(out, tc.expected_output):
            debug = f"\n--- TEST {tc.id} FAILED ---\nInput:\n{tc.input_data}\nExpected:\n{tc.expected_output}\nGot:\n{out}\nSTDERR:\n{err}"
            return ("Wrong Answer", total_time, passed, total, debug)

        passed += 1

    return ("Accepted", total_time, passed, total, "OK")
