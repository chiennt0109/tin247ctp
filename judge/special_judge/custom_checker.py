import subprocess
import time

from .compiler import ensure_custom_checker
from .result import SpecialJudgeResult
from .tempfiles import checker_tempfiles
from .utils import parse_config


def run_custom_checker(problem_code: str, input_data: str, output_data: str, expected_data: str, config: str = "") -> SpecialJudgeResult:
    checker_path, err = ensure_custom_checker(problem_code)
    if not checker_path:
        return SpecialJudgeResult(return_code=3, stderr=err, mode="custom")

    cfg = parse_config(config)
    order = cfg.get("custom_order", cfg.get("checker_order", "in_out_exp"))
    start = time.perf_counter()

    with checker_tempfiles(input_data, output_data, expected_data) as (in_path, out_path, exp_path):
        if order == "in_exp_out":
            argv = [checker_path, in_path, exp_path, out_path]
        else:
            argv = [checker_path, in_path, out_path, exp_path]

        try:
            proc = subprocess.run(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=1.0,
            )
            elapsed = time.perf_counter() - start
            return SpecialJudgeResult(return_code=proc.returncode, stdout=proc.stdout, stderr=proc.stderr, time=elapsed, mode="custom")
        except subprocess.TimeoutExpired:
            elapsed = time.perf_counter() - start
            return SpecialJudgeResult(return_code=3, stderr="checker timeout > 1s", time=elapsed, mode="custom")
        except Exception as exc:
            elapsed = time.perf_counter() - start
            return SpecialJudgeResult(return_code=3, stderr=f"checker execution error: {exc}", time=elapsed, mode="custom")
