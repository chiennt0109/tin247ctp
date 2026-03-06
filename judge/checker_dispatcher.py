from __future__ import annotations

import os

from judge.builtin_checkers import BUILTIN_CHECKER_NAMES, run_builtin_checker
from judge.special_judge.custom_checker import run_custom_checker


CHECKER_NONE = "none"


def resolve_checker_mode(problem_code: str, checker_type: str) -> str:
    c = (checker_type or CHECKER_NONE).strip().lower()
    if c in BUILTIN_CHECKER_NAMES:
        return "builtin"
    tc_dir = f"/srv/judge/testcases/{problem_code}"
    if os.path.exists(f"{tc_dir}/checker") or os.path.exists(f"{tc_dir}/checker.cpp") or os.path.exists(f"{tc_dir}/checker.py"):
        return "custom"
    return "diff"


def run_checker(problem_code: str, checker_type: str, input_data: str, contestant_output: str, expected_output: str, config: str = "") -> dict:
    mode = resolve_checker_mode(problem_code, checker_type)
    if mode == "builtin":
        res = run_builtin_checker(checker_type, input_data, contestant_output, expected_output, config)
        res["checker_mode"] = "builtin"
        return res
    if mode == "custom":
        res = run_custom_checker(problem_code, input_data, contestant_output, expected_output, config)
        res = res.to_dict()
        res["checker_mode"] = "custom"
        return res
    ok = (contestant_output or "").strip().replace("\r\n", "\n").rstrip() == (expected_output or "").strip().replace("\r\n", "\n").rstrip()
    return {
        "checker_mode": "diff",
        "return_code": 0 if ok else 1,
        "stdout": "",
        "stderr": "",
        "time": 0.0,
    }
