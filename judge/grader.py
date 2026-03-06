# path: judge/grader.py
from __future__ import annotations

import os
from typing import Tuple

from problems.models import TestCase

from .checker_dispatcher import run_checker
from .debug_logger import log_test_event
from .dispatcher import JudgeDispatcher
from .result import SubmissionResult, TestResult
from .runner import compile_submission, run_case
from .verdict import map_checker_exit_code, map_program_exit_code

CHECKER_NONE = "none"


def normalize(s):
    return (s or "").strip().replace("\r\n", "\n").rstrip()


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
    except Exception:
        return None, None
    return checker, config


def _resolve_checker(problem):
    checker_type = getattr(problem, "checker", None)
    checker_config = getattr(problem, "checker_config", "") or ""

    yml_checker, yml_config = _load_problem_yml_checker(problem.code)
    if yml_checker:
        checker_type = yml_checker
    if yml_config:
        checker_config = yml_config

    checker_type = (checker_type or CHECKER_NONE).strip().lower()
    return checker_type, checker_config


def grade_submission(submission) -> Tuple[str, float, int, int, str]:
    problem = submission.problem
    tests = list(TestCase.objects.filter(problem=problem))
    total_tests = len(tests)
    if total_tests == 0:
        return ("No Test Cases", 0.0, 0, 0, "")

    bundle, compile_err = compile_submission(submission.language, submission.source_code)
    if bundle is None:
        return ("Compilation Error", 0.0, 0, total_tests, compile_err)

    checker_type, checker_config = _resolve_checker(problem)

    aggregate = SubmissionResult(total_tests=total_tests)
    debug_log = []

    dispatcher = JudgeDispatcher()

    def _run_in_worker(_ctx):
        for idx, tc in enumerate(tests, start=1):
            prog = run_case(bundle, tc.input_data, time_limit=float(problem.time_limit or 1.0))
            program_verdict = map_program_exit_code(int(prog.get("return_code", 1)))

            checker_result = {
                "checker_mode": "skipped",
                "return_code": 1,
                "stdout": "",
                "stderr": "",
                "time": 0.0,
            }

            if program_verdict == "OK":
                checker_result = run_checker(
                    problem.code,
                    checker_type,
                    tc.input_data,
                    prog.get("stdout", ""),
                    tc.expected_output,
                    checker_config,
                )
                final_verdict = map_checker_exit_code(int(checker_result.get("return_code", 1)))
            else:
                final_verdict = program_verdict

            tr = TestResult(
                test_id=idx,
                input_size=len(tc.input_data or ""),
                execution_time=float(prog.get("time", 0.0) or 0.0),
                program_exit_code=int(prog.get("return_code", 1)),
                checker_type=checker_result.get("checker_mode", checker_type),
                checker_exit_code=int(checker_result.get("return_code", 1)),
                checker_stdout=checker_result.get("stdout", ""),
                checker_stderr=checker_result.get("stderr", ""),
                verdict=final_verdict,
            )
            aggregate.add(tr)

            log_test_event(
                {
                    "submission_id": submission.id,
                    "problem_code": problem.code,
                    "test_id": idx,
                    "input_size": tr.input_size,
                    "program_exit_code": tr.program_exit_code,
                    "execution_time": tr.execution_time,
                    "checker_type": tr.checker_type,
                    "checker_exit_code": tr.checker_exit_code,
                    "stdout_preview": (prog.get("stdout", "") or "")[:200],
                    "stderr_preview": (prog.get("stderr", "") or "")[:200],
                }
            )

            debug_log.append(
                f"[TEST {idx}] time={tr.execution_time:.3f}s\n"
                f"IN:\n{tc.input_data}\n"
                f"OUT:\n{prog.get('stdout','')}\n"
                f"EXP:\n{tc.expected_output}\n"
                f"program_exit_code: {tr.program_exit_code}\n"
                f"checker_mode: {tr.checker_type}\n"
                f"checker_exit_code: {tr.checker_exit_code}\n"
                f"checker_stdout: {tr.checker_stdout}\n"
                f"checker_stderr: {tr.checker_stderr}\n"
                f"checker_time: {checker_result.get('time',0.0)}\n"
                f"verdict: {tr.verdict}\n---\n"
            )

            if final_verdict != "Accepted":
                break

    dispatcher.dispatch(submission.id, _run_in_worker)
    aggregate.finalize()

    return (
        aggregate.verdict,
        round(aggregate.max_time, 3),
        aggregate.passed_tests,
        aggregate.total_tests,
        "\n".join(debug_log[:10]),
    )
