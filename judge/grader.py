from problems.models import TestCase
from .run_code import run_program
import time


def normalize(s: str) -> str:
    return (s or "").strip().replace('\r\n','\n').rstrip()


def grade_submission(submission):
    problem = submission.problem
    testcases = TestCase.objects.filter(problem=problem)
    total_time = 0.0

    for tc in testcases:
        start = time.time()
        out, _ = run_program(submission.language, submission.source_code, tc.input_data, time_limit=problem.time_limit)
        elapsed = max(0.0, time.time() - start)
        total_time += elapsed

        if out in ("Time Limit Exceeded",) or out.startswith("Compilation Error") or out.startswith("Runtime Error"):
            return (out, total_time)

        if normalize(out) != normalize(tc.expected_output):
            return ("Wrong Answer", total_time)

    return ("Accepted", total_time)
