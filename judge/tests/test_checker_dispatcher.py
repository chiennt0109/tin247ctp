import unittest

from judge.checker_dispatcher import resolve_checker_mode


class CheckerDispatcherTests(unittest.TestCase):
    def test_builtin_mode(self):
        self.assertEqual(resolve_checker_mode("NOPE", "permutation"), "builtin")

    def test_diff_mode_for_none(self):
        self.assertEqual(resolve_checker_mode("NOPE", "none"), "diff")


if __name__ == "__main__":
    unittest.main()
