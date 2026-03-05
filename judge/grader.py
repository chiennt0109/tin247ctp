# path: judge/grader.py
from problems.models import TestCase
from .run_code import run_program
import time
import signal
import subprocess

def normalize(s):
    return (s or "").strip().replace('\r\n', '\n').rstrip()


def grade_submission(submission):
    """
    Chấm bài cho 1 submission, có giới hạn thời gian và kiểm soát tiến trình.
    """
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

    # 🚀 Compile một lần (C++)
    compiled_bin = None
    if lang == "cpp":
        out, err = run_program("compile_cpp", code, "")
        if "Compilation Error" in out:
            return ("Compilation Error", 0, 0, total_tests, out)
        compiled_bin = err.strip()  # err chứa đường dẫn file nhị phân

    # ⚙️ Chạy từng test case
    for idx, tc in enumerate(tests, start=1):
        start = time.time()
        verdict = "Accepted"

        try:
            # mỗi test chỉ chạy tối đa time_limit + 0.5s buffer
            hard_limit = min(max(problem.time_limit or 1.0, 0.5), 5.0) + 0.5

            if lang == "cpp":
                out, err = run_program(
                    "run_cpp_bin", compiled_bin, tc.input_data,
                    time_limit=hard_limit
                )
            else:
                out, err = run_program(
                    lang, code, tc.input_data,
                    time_limit=hard_limit
                )

            elapsed = time.time() - start
            total_time += elapsed

            debug_log.append(
                f"[TEST {idx}] time={elapsed:.3f}s\nIN:\n{tc.input_data}\nOUT:\n{out}\nEXP:\n{tc.expected_output}\n---\n"
            )

            # kiểm tra lỗi runtime hoặc timeout
            if "Time Limit" in out:
                verdict = "Time Limit Exceeded"
                break
            elif "Runtime Error" in out:
                verdict = "Runtime Error"
                break
            elif "API Error" in out or "Internal Error" in out:
                verdict = "Judge Error"
                break

            # so sánh kết quả
            if normalize(out) == normalize(tc.expected_output):
                passed += 1
            else:
                verdict = "Wrong Answer"

        except subprocess.TimeoutExpired:
            verdict = "Time Limit Exceeded"
            total_time += hard_limit
            debug_log.append(f"[TEST {idx}] TIMEOUT (>{hard_limit}s)\n")
            break

        except Exception as e:
            verdict = f"Runtime Error: {e}"
            debug_log.append(f"[TEST {idx}] {verdict}\n")
            break

    # 🧩 Tổng kết
    if passed == total_tests:
        verdict = "Accepted"
    elif "Time Limit" in verdict:
        verdict = "Time Limit Exceeded"
    elif "Runtime" in verdict:
        verdict = "Runtime Error"
    elif "Judge Error" in verdict:
        verdict = "Judge Error"
    elif passed < total_tests:
        verdict = "Wrong Answer"

    # ✨ Trả kết quả
    return (
        verdict,
        round(total_time, 3),
        passed,
        total_tests,
        "\n".join(debug_log[:10])  # chỉ log tối đa 10 test để tránh tràn DB
    )
