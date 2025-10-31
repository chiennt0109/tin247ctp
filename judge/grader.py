from problems.models import TestCase
from .run_code import run_program
import time

def normalize(s):
    return (s or "").strip().replace('\r\n', '\n').rstrip()

def grade_submission(submission):
    problem = submission.problem
    tests = TestCase.objects.filter(problem=problem)
    lang = submission.language
    code = submission.source_code

    total_tests = tests.count()
    if total_tests == 0:
        return ("No Test Cases", 0, 0, 0, "")

    passed = 0
    total_time = 0.0
    debug_log = []

    # 🔥 Compile once for C++
    compiled_bin = None
    if lang == "cpp":
        out, err = run_program("compile_cpp", code, "")
        if "Compilation Error" in out:
            return ("Compilation Error", 0, 0, total_tests, out)

        # Saved binary path
        compiled_bin = err.strip()  # err used to return binary path

    for tc in tests:
        start = time.time()

        if lang == "cpp":
            out, err = run_program("run_cpp_bin", compiled_bin, tc.input_data, time_limit=problem.time_limit)
        else:
            out, err = run_program(lang, code, tc.input_data, time_limit=problem.time_limit)

        elapsed = time.time() - start
        total_time += elapsed

        debug_log.append(f"IN:\n{tc.input_data}\nOUT:\n{out}\nEXP:\n{tc.expected_output}\n---\n")

        # timeout / runtime / API errors
        if any(key in out for key in ["Time Limit", "Runtime Error", "API Error", "Internal Error"]):
            return (out, total_time, passed, total_tests, "\n".join(debug_log[:5]))

        if normalize(out) == normalize(tc.expected_output):
            passed += 1

    verdict = "Accepted" if passed == total_tests else "Wrong Answer"
    return (verdict, total_time, passed, total_tests, "\n".join(debug_log[:5]))
