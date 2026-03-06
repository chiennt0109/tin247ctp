from __future__ import annotations

import json
import logging

from problems.models import TestCase
from submissions.models import Submission

from judge.checker import CheckerService
from judge.debug_logger import log_test_event
from judge.result import SubmissionResult, TestResult, VERDICT_TO_DB
from judge.runner import compile_submission, run_case
from judge.sandbox import SandboxManager

logger = logging.getLogger(__name__)


def _map_program_verdict(return_code: int) -> str:
    if return_code == 0:
        return "AC"
    if return_code == 124:
        return "TLE"
    if return_code == 137:
        return "MLE"
    return "RE"


def _map_checker_verdict(return_code: int) -> str:
    if return_code == 0:
        return "AC"
    if return_code == 2:
        return "PE"
    if return_code == 1:
        return "WA"
    return "JE"


def judge_submission_job(submission_id: int) -> dict:
    logger.info("[TASK] submission start id=%s", submission_id)
    submission = Submission.objects.select_related("problem").get(id=submission_id)
    problem = submission.problem
    tests = list(TestCase.objects.filter(problem=problem).order_by("id"))

    if not tests:
        payload = {"verdict": "JE", "time": 0.0, "memory": 0, "passed": 0, "total": 0}
        submission.verdict = "Judge Error"
        submission.debug_info = "No testcases configured"
        submission.save(update_fields=["verdict", "debug_info"])
        return payload

    sandbox = SandboxManager()
    checker = CheckerService()
    ctx = sandbox.create(submission_id)

    try:
        logger.info("[TASK] compile id=%s", submission_id)
        bundle, compile_error = compile_submission(submission.language, submission.source_code, ctx.root_dir)
        if bundle is None:
            payload = {"verdict": "CE", "time": 0.0, "memory": 0, "passed": 0, "total": len(tests)}
            submission.verdict = "Compilation Error"
            submission.exec_time = 0
            submission.passed_tests = 0
            submission.total_tests = len(tests)
            submission.debug_info = compile_error[:8000]
            submission.save(update_fields=["verdict", "exec_time", "passed_tests", "total_tests", "debug_info"])
            return payload

        aggregate = SubmissionResult(total_tests=len(tests))
        debug_rows = []

        for index, tc in enumerate(tests, start=1):
            logger.info("[TASK] run test %s submission=%s", index, submission_id)
            run_res = run_case(
                bundle=bundle,
                input_data=tc.input_data,
                time_limit=float(problem.time_limit or 1),
                memory_limit_mb=int(problem.memory_limit or 256),
            )

            program_verdict = _map_program_verdict(int(run_res.get("return_code", 1)))
            checker_exit = -1
            final_verdict = program_verdict

            if program_verdict == "AC":
                logger.info("[TASK] checker submission=%s test=%s", submission_id, index)
                checker_res = checker.run(
                    problem_code=problem.code,
                    checker_type=problem.checker,
                    checker_config=problem.checker_config,
                    input_data=tc.input_data,
                    user_output=run_res.get("stdout", ""),
                    expected_output=tc.expected_output,
                    submission_id=submission_id,
                    test_id=index,
                )
                checker_exit = int(checker_res.get("return_code", 1))
                final_verdict = _map_checker_verdict(checker_exit)

            tr = TestResult(
                test_id=index,
                execution_time=float(run_res.get("time", 0.0) or 0.0),
                memory_kb=int(run_res.get("memory_kb", 0) or 0),
                program_exit_code=int(run_res.get("return_code", 1)),
                checker_exit_code=checker_exit,
                verdict=final_verdict,
                stdout=(run_res.get("stdout", "") or "")[:500],
                stderr=(run_res.get("stderr", "") or "")[:500],
            )
            aggregate.add(tr)
            log_test_event(
                {
                    "event": "judge_test",
                    "submission_id": submission_id,
                    "test_id": index,
                    "program_exit": tr.program_exit_code,
                    "checker_exit": tr.checker_exit_code,
                    "verdict": tr.verdict,
                    "time": tr.execution_time,
                    "memory_kb": tr.memory_kb,
                }
            )
            debug_rows.append({
                "test": index,
                "verdict": final_verdict,
                "time": tr.execution_time,
                "memory_kb": tr.memory_kb,
                "stdout": tr.stdout,
                "stderr": tr.stderr,
            })

            if final_verdict != "AC":
                break

        aggregate.finalize()
        payload = aggregate.to_payload()
        submission.verdict = VERDICT_TO_DB.get(payload["verdict"], "Judge Error")
        submission.exec_time = payload["time"]
        submission.passed_tests = payload["passed"]
        submission.total_tests = payload["total"]
        submission.debug_info = json.dumps({"summary": payload, "tests": debug_rows}, ensure_ascii=False)
        submission.save(update_fields=["verdict", "exec_time", "passed_tests", "total_tests", "debug_info"])

        logger.info("[TASK] result submission=%s payload=%s", submission_id, payload)
        return payload
    finally:
        sandbox.destroy(ctx)
