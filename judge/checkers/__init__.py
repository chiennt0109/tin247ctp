from __future__ import annotations

import os
import subprocess
import tempfile
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


def run_custom_checker(problem_code: str, input_data: str, contestant_output: str, expected_output: str, timeout: float = 1.0) -> Dict[str, object]:
    checker_bin = f"/srv/judge/testcases/{problem_code}/checker"
    if not os.path.exists(checker_bin):
        return {"return_code": 1, "stdout": "", "stderr": f"Custom checker not found: {checker_bin}"}

    with tempfile.TemporaryDirectory() as tmpdir:
        in_path = os.path.join(tmpdir, "input.txt")
        out_path = os.path.join(tmpdir, "contestant.txt")
        ans_path = os.path.join(tmpdir, "expected.txt")
        for path, content in [(in_path, input_data), (out_path, contestant_output), (ans_path, expected_output)]:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content or "")

        proc = subprocess.run(
            [checker_bin, in_path, out_path, ans_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        return {
            "return_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
