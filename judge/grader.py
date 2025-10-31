# path: judge/grader.py
import time, json
from .run_code import run_program
from problems.models import TestCase

def grade_submission(submission):
    problem = submission.problem
    tests = TestCase.objects.filter(problem=problem).order_by("id")

    passed = 0
    total = 0
    debug = []
    start_time = time.time()

    for t in tests:
        total += 1

        # Run user code on this testcase
        out, err = run_program(
            submission.language,
            submission.source_code,
            t.input_data,
            time_limit=problem.time_limit
        )

        # Normalize output to compare
        out_clean = out.replace("\r", "").strip() if out else ""
        expected = t.expected_output.replace("\r", "").strip()

        # Collect debug result
        debug.append({
            "test_id": t.id,
            "input": t.input_data,
            "expected": expected,
            "got": out_clean,
            "stderr": err,
            "status": "✅" if out_clean == expected else "❌"
        })

        # Count passed
        if out_clean == expected:
            passed += 1

    exec_time = round(time.time() - start_time, 4)

    # Final verdict
    if passed == total:
        verdict = "Accepted"
    else:
        verdict = "Wrong Answer"

    return (
        verdict,
        exec_time,
        passed,
        total,
        json.dumps(debug, ensure_ascii=False)
    )
