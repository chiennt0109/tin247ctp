from judge.special_judge.builtin_checkers import run_builtin_checker

BUILTIN_CHECKER_NAMES = {
    "permutation",
    "set_compare",
    "numeric_tolerance",
    "float_tolerance",
    "euler_path",
    "graph_path",
    "matching",
    "constructive",
    "grid",
    "geometry",
    "tree",
}

__all__ = ["run_builtin_checker", "BUILTIN_CHECKER_NAMES"]
