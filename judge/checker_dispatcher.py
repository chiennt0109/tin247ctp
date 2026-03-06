from __future__ import annotations

import os
import subprocess
import tempfile

from judge.builtin_checkers import BUILTIN_CHECKER_NAMES, run_builtin_checker
from judge.debug_logger import log_test_event
from judge.special_judge.compiler import ensure_custom_checker

CHECKER_NONE = "none"
TMP_ROOT = "/dev/shm/judge_tmp"


def _normalize_text(s: str) -> str:
    return (s or "").strip().replace("\r\n", "\n").rstrip()


def resolve_checker_mode(problem_code: str, checker_type: str) -> str:
    c = (checker_type or CHECKER_NONE).strip().lower()
    if c in BUILTIN_CHECKER_NAMES:
        return "builtin"
    tc_dir = f"/srv/judge/testcases/{problem_code}"
    if os.path.exists(f"{tc_dir}/checker") or os.path.exists(f"{tc_dir}/checker.cpp") or os.path.exists(f"{tc_dir}/checker.py"):
        return "custom"
    return "diff"


def _run_custom_checker_cmd(
    checker_path: str,
    input_data: str,
    contestant_output: str,
    expected_output: str,
    submission_id: int | None,
    test_id: int | None,
) -> dict:
    os.makedirs(TMP_ROOT, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="checker_", dir=TMP_ROOT) as td:
        input_file = os.path.join(td, "input.txt")
        user_output_file = os.path.join(td, "user_output.txt")
        answer_file = os.path.join(td, "answer.txt")

        with open(input_file, "w", encoding="utf-8") as f:
            f.write(input_data or "")
        with open(user_output_file, "w", encoding="utf-8") as f:
            f.write(contestant_output or "")
        with open(answer_file, "w", encoding="utf-8") as f:
            f.write(expected_output or "")

        cmd = [checker_path, input_file, user_output_file, answer_file]

        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=2,
            )
            stdout = (proc.stdout or b"").decode("utf-8", errors="replace")
            stderr = (proc.stderr or b"").decode("utf-8", errors="replace")
            rc = int(proc.returncode)
        except subprocess.TimeoutExpired as exc:
            rc = 3
            stdout = (exc.stdout or b"").decode("utf-8", errors="replace")
            stderr = ((exc.stderr or b"").decode("utf-8", errors="replace") + "\nchecker timeout > 2s").strip()
        except Exception as exc:
            rc = 3
            stdout = ""
            stderr = f"checker execution error: {exc}"

        log_test_event(
            {
                "submission_id": submission_id,
                "test_id": test_id,
                "event": "checker_run",
                "cmd": cmd,
                "return_code": rc,
                "stdout": stdout,
                "stderr": stderr,
            }
        )

        return {
            "checker_mode": "custom",
            "return_code": rc,
            "stdout": stdout,
            "stderr": stderr,
            "time": 0.0,
        }


def run_checker(
    problem_code: str,
    checker_type: str,
    input_data: str,
    contestant_output: str,
    expected_output: str,
    config: str = "",
    submission_id: int | None = None,
    test_id: int | None = None,
) -> dict:
    mode = resolve_checker_mode(problem_code, checker_type)

    if mode == "builtin":
        res = run_builtin_checker(checker_type, input_data, contestant_output, expected_output, config)
        res["checker_mode"] = "builtin"
        return res

    if mode == "custom":
        checker_path, _err = ensure_custom_checker(problem_code)
        if checker_path and os.path.exists(checker_path):
            return _run_custom_checker_cmd(
                checker_path,
                input_data,
                contestant_output,
                expected_output,
                submission_id,
                test_id,
            )

        # fallback to builtin checker when custom checker binary is unavailable
        c = (checker_type or "").strip().lower()
        if c in BUILTIN_CHECKER_NAMES:
            res = run_builtin_checker(c, input_data, contestant_output, expected_output, config)
            res["checker_mode"] = "builtin_fallback"
            return res

    ok = _normalize_text(contestant_output) == _normalize_text(expected_output)
    return {
        "checker_mode": "diff",
        "return_code": 0 if ok else 1,
        "stdout": "",
        "stderr": "",
        "time": 0.0,
    }
