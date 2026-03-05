from .builtin_checkers import run_builtin_checker
from .custom_checker import run_custom_checker
from .result import SpecialJudgeResult

CHECKER_NONE = "none"
CHECKER_CUSTOM = "custom"


def run_special_judge(problem_code, checker_type, input_data, contestant_output, expected_output, config=""):
    checker_type = (checker_type or CHECKER_NONE).strip().lower()

    if checker_type == CHECKER_NONE:
        return SpecialJudgeResult(return_code=3, stderr="special judge called with none", mode="none").to_dict()

    if checker_type == CHECKER_CUSTOM:
        return run_custom_checker(problem_code, input_data, contestant_output, expected_output, config=config).to_dict()

    return run_builtin_checker(checker_type, input_data, contestant_output, expected_output, config=config).to_dict()
