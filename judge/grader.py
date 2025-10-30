# path: judge/grader.py
from problems.models import TestCase
from judge.run_code import run_program
import time

def _clean(s):
    if s is None: return ""
    s = s.replace("\r\n", "\n")
    lines = s.split("\n")
    while lines and lines[-1].strip() == "":
        lines.pop()
    return "\n".join(line.rstrip() for line in lines)

def grade_submission(submission):
    problem = submission.problem
    tests = TestCase.objects.filter(problem=problem).order_by("id")
    total = tests.count()
    passed = 0
    total_time = 0.0

    for tc in tests:
        start = time.time()
        out, _ = run_program(
            submission.language,
            submission.source_code,
            tc.input_data,
            time_limit=problem.time_limit
        )
        total_time += max(0, time.time() - start)

        if out.startswith("Compilation Error"):
            return ("Compilation Error", total_time, passed, total)
        if out.startswith("Runtime Error"):
            return ("Runtime Error", total_time, passed, total)
        if out == "Time Limit Exceeded":
            return ("Time Limit Exceeded", total_time, passed, total)
        if out.startswith("API Error") or out.startswith("Internal Error"):
            return ("Runtime Error", total_time, passed, total)

        if _clean(out) != _clean(tc.expected_output):
            return ("Wrong Answer", total_time, passed, total)

        passed += 1

    return ("Accepted", total_time, passed, total)
