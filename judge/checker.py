from __future__ import annotations

from judge.checker_dispatcher import run_checker as _run_checker


class CheckerService:
    """Checker facade: standard diff + special judge."""

    def run(
        self,
        problem_code: str,
        checker_type: str,
        input_data: str,
        user_output: str,
        expected_output: str,
        checker_config: str = "",
        submission_id: int | None = None,
        test_id: int | None = None,
    ) -> dict:
        return _run_checker(
            problem_code=problem_code,
            checker_type=checker_type,
            input_data=input_data,
            contestant_output=user_output,
            expected_output=expected_output,
            config=checker_config,
            submission_id=submission_id,
            test_id=test_id,
        )
