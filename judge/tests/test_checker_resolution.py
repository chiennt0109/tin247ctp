import unittest

from judge.checker_dispatcher import canonicalize_checker_type, resolve_checker_mode, run_checker


class CheckerResolutionTests(unittest.TestCase):
    def test_canonicalize_checker_alias_with_spaces(self):
        self.assertEqual(canonicalize_checker_type("Euler Path"), "euler_path")

    def test_resolve_builtin_mode_from_alias(self):
        self.assertEqual(resolve_checker_mode("NOPE", "Euler Path"), "builtin")

    def test_run_checker_supports_alias_name(self):
        # n=3,m=2 edges (1,2),(2,3)
        res = run_checker("NOPE", "Euler Path", "3 2 1 2 2 3", "1 2 3", "")
        self.assertEqual(res["checker_mode"], "builtin")
        self.assertEqual(res["return_code"], 0)


if __name__ == "__main__":
    unittest.main()
