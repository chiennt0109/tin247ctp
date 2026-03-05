# path: judge/grader.py
import os
import time
import subprocess

from problems.models import TestCase
from .run_code import run_program
from .checkers import run_builtin_checker, run_custom_checker

CHECKER_NONE = "none"
CHECKER_CUSTOM = "custom"


def normalize(s):
    return (s or "").strip().replace('\r\n', '\n').rstrip()


def _load_problem_yml_checker(problem_code: str):
    path = f"/srv/judge/testcases/{problem_code}/problem.yml"
    if not os.path.exists(path):
        return None, None
    checker = None
    config = None
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or ":" not in line:
                    continue
                k, v = [x.strip() for x in line.split(":", 1)]
                if k == "checker":
                    checker = v
                elif k in ("checker_config", "epsilon"):
                    config = f"eps={v}" if k == "epsilon" else v
                elif k == "checker_file" and v:
                    # supported via uploaded binary in sandbox path
                    pass
    except Exception:
        return None, None
    return checker, config


def _check_output(problem, tc, contestant_output):
    checker_type = getattr(problem, "checker_type", CHECKER_NONE) or CHECKER_NONE
    checker_config = getattr(problem, "checker_config", "") or ""
    if checker_type == CHECKER_NONE:
        yml_checker, yml_config = _load_problem_yml_checker(problem.code)
        if yml_checker:
            checker_type = yml_checker
        if yml_config:
            checker_config = yml_config

    if checker_type == CHECKER_NONE:
        ok = normalize(contestant_output) == normalize(tc.expected_output)
        return ok, {"mode": "diff", "return_code": 0 if ok else 1, "stdout": "", "stderr": ""}

    if checker_type == CHECKER_CUSTOM:
        log = run_custom_checker(problem.code, tc.input_data, contestant_output, tc.expected_output, timeout=1.0)
    else:
        log = run_builtin_checker(checker_type, tc.input_data, contestant_output, tc.expected_output, config=checker_config)

    # 0 -> AC, 1/2 -> WA
    ok = int(log.get("return_code", 1)) == 0
    log["mode"] = f"checker:{checker_type}"
    return ok, log


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

    compiled_bin = None
    if lang == "cpp":
        out, err = run_program("compile_cpp", code, "")
        if "Compilation Error" in out:
            return ("Compilation Error", 0, 0, total_tests, out)
        compiled_bin = err.strip()

    verdict = "Accepted"
    for idx, tc in enumerate(tests, start=1):
        start = time.time()
        try:
            hard_limit = min(max(problem.time_limit or 1.0, 0.5), 5.0) + 0.5
            if lang == "cpp":
                out, err = run_program("run_cpp_bin", compiled_bin, tc.input_data, time_limit=hard_limit)
            else:
                out, err = run_program(lang, code, tc.input_data, time_limit=hard_limit)

            elapsed = time.time() - start
            total_time += elapsed

            if "Time Limit" in out:
                verdict = "Time Limit Exceeded"
                debug_log.append(f"[TEST {idx}] TIMEOUT\n")
                break
            if "Runtime Error" in out:
                verdict = "Runtime Error"
                debug_log.append(f"[TEST {idx}] Runtime Error: {err}\n")
                break
            if "API Error" in out or "Internal Error" in out:
                verdict = "Judge Error"
                debug_log.append(f"[TEST {idx}] Judge Error: {out}\n")
                break

            ok, checker_log = _check_output(problem, tc, out)
            debug_log.append(
                f"[TEST {idx}] time={elapsed:.3f}s\n"
                f"IN:\n{tc.input_data}\nOUT:\n{out}\nEXP:\n{tc.expected_output}\n"
                f"checker_input: mode={checker_log.get('mode')}\n"
                f"checker_output: {checker_log.get('stdout','')}\n"
                f"checker_error: {checker_log.get('stderr','')}\n---\n"
            )

            if ok:
                passed += 1
            else:
                verdict = "Wrong Answer"
                break

        except subprocess.TimeoutExpired:
            verdict = "Time Limit Exceeded"
            total_time += hard_limit
            debug_log.append(f"[TEST {idx}] TIMEOUT (>{hard_limit}s)\n")
            break
        except Exception as e:
            verdict = f"Runtime Error: {e}"
            debug_log.append(f"[TEST {idx}] {verdict}\n")
            break

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

    return verdict, round(total_time, 3), passed, total_tests, "\n".join(debug_log[:10])
