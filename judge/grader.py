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

    while u and u[-1] == "":
        u.pop()
    while e and e[-1] == "":
        e.pop()

    return u == e

def grade_submission(submission):
    problem = submission.problem
    tests = TestCase.objects.filter(problem=problem).order_by("id")

    total = tests.count()
    passed = 0
    total_time = 0
    debug_info = []  # ✅ lưu tất cả test debug

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

        record = {
            "tc": tc.id,
            "input": tc.input_data,
            "expected": tc.expected_output.strip(),
            "output": normalize(out),
            "stderr": err.strip() if err else ""
        }

        # ✅ Compilation Error
        if out.startswith("Compilation Error"):
            record["error"] = "Compile Error"
            debug_info.append(record)
            return ("Compilation Error", total_time, passed, total, debug_info)

        # ✅ Runtime Error
        if out.startswith("Runtime Error"):
            record["error"] = "Runtime Error"
            debug_info.append(record)
            return ("Runtime Error", total_time, passed, total, debug_info)

        # ✅ Time Limit
        if out == "Time Limit Exceeded":
            record["error"] = "TLE"
            debug_info.append(record)
            return ("Time Limit Exceeded", total_time, passed, total, debug_info)

        # ✅ API Error (Judge0)
        if out.startswith("API Error"):
            record["error"] = "API Error"
            debug_info.append(record)
            return ("Runtime Error", total_time, passed, total, debug_info)

        # ✅ Compare output
        if not compare_output(out, tc.expected_output):
            record["error"] = "Wrong Answer"
            debug_info.append(record)
            return ("Wrong Answer", total_time, passed, total, debug_info)

        # ✅ AC test này
        record["error"] = "OK"
        debug_info.append(record)
        passed += 1

    return ("Accepted", total_time, passed, total, debug_info)
