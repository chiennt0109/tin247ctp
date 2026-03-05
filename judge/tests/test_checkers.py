import unittest

from judge.checkers import run_builtin_checker


class BuiltinCheckerTests(unittest.TestCase):
    def test_permutation_accept(self):
        res = run_builtin_checker("permutation", "5", "1 3 2 5 4", "")
        self.assertEqual(res["return_code"], 0)

    def test_set_compare_accept_order_insensitive(self):
        res = run_builtin_checker("set_compare", "", "3 1 2", "1 2 3")
        self.assertEqual(res["return_code"], 0)

    def test_numeric_tolerance(self):
        res = run_builtin_checker("numeric_tolerance", "", "3.141592", "3.141593", config="eps=0.00001")
        self.assertEqual(res["return_code"], 0)

    def test_euler_path_reject_wrong_length(self):
        # n=3,m=2 edges (1,2),(2,3), path length must be 3
        res = run_builtin_checker("euler_path", "3 2 1 2 2 3", "1 2", "")
        self.assertEqual(res["return_code"], 1)


if __name__ == "__main__":
    unittest.main()
