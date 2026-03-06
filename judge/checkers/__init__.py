from __future__ import annotations

import os
import subprocess
from typing import Dict

from .builtins import BUILTIN_CHECKERS


def run_builtin_checker(name: str, input_data: str, contestant_output: str, expected_output: str, config: str = "") -> Dict[str, object]:
    fn = BUILTIN_CHECKERS.get(name)
    if not fn:
        return {"return_code": 1, "stdout": "", "stderr": f"Unknown checker: {name}"}
    try:
        rc, msg = fn(input_data, contestant_output, expected_output, config=config or "")
        return {"return_code": int(rc), "stdout": msg, "stderr": ""}
    except Exception as exc:
        return {"return_code": 1, "stdout": "", "stderr": f"Checker exception: {exc}"}


def _ensure_custom_checker_binary(problem_code: str) -> tuple[str | None, str]:
    checker_dir = f"/srv/judge/testcases/{problem_code}"
    checker_bin = os.path.join(checker_dir, "checker")
    checker_cpp = os.path.join(checker_dir, "checker.cpp")

    if os.path.exists(checker_bin):
        return checker_bin, ""

    if os.path.exists(checker_cpp):
        try:
            proc = subprocess.run(
                ["g++", checker_cpp, "-O2", "-std=c++17", "-o", checker_bin],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15,
            )
        except Exception as exc:
            return None, f"Failed to compile checker.cpp: {exc}"

        if proc.returncode != 0:
            return None, f"checker.cpp compile error: {proc.stderr}"

        os.chmod(checker_bin, 0o755)
        return checker_bin, ""

    return None, f"Custom checker not found: {checker_bin} (and checker.cpp missing)"


def run_custom_checker(problem_code: str, input_data: str, contestant_output: str, expected_output: str, timeout: float = 1.0, config: str = "") -> Dict[str, object]:
    checker_bin, ensure_err = _ensure_custom_checker_binary(problem_code)
    if not checker_bin:
        return {"return_code": 1, "stdout": "", "stderr": ensure_err}

    in_path = "/tmp/judge_input.txt"
    out_path = "/tmp/judge_output.txt"
    ans_path = "/tmp/judge_expected.txt"

    for path, content in [(in_path, input_data), (out_path, contestant_output), (ans_path, expected_output)]:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content or "")

    order = "in_out_exp"
    cfg = (config or "").lower()
    if "custom_order=in_exp_out" in cfg or "checker_order=in_exp_out" in cfg:
        order = "in_exp_out"

    argv = [checker_bin, in_path, out_path, ans_path] if order == "in_out_exp" else [checker_bin, in_path, ans_path, out_path]

    try:
        proc = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"return_code": 1, "stdout": "", "stderr": f"Custom checker timeout > {timeout}s"}
    except Exception as exc:
        return {"return_code": 1, "stdout": "", "stderr": f"Custom checker execution error: {exc}"}

    return {
        "return_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }
