from problems.models import TestCase
from .run_code import run_program
import time

def normalize(s: str) -> str:
    return (s or "").strip().replace('\r\n', '\n').rstrip()

def grade_submission(submission):
    problem = submission.problem
    testcases = TestCase.objects.filter(problem=problem)
    total_time = 0.0
    passed = 0
    failed = 0
    details = []

    for tc in testcases:
        start = time.time()
        out, _ = run_program(submission.language, submission.source_code, tc.input_data, time_limit=problem.time_limit)
        elapsed = max(0.0, time.time() - start)
        total_time += elapsed

        if out in ("Time Limit Exceeded",) or out.startswith("Compilation") or out.startswith("Runtime"):
            details.append({"ok": False, "time": elapsed, "output": out})
            failed += 1
            return (out, total_time, passed, failed)

        if normalize(out) == normalize(tc.expected_output):
            passed += 1
            details.append({"ok": True, "time": elapsed, "output": out})
        else:
            failed += 1
            details.append({"ok": False, "time": elapsed, "output": out})

    verdict = "Accepted" if failed == 0 else "Wrong Answer"
    submission.test_details = details  # giữ trong context, không cần DB field
    return (verdict, total_time, passed, failed)
