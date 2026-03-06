import unittest

from judge.verdict import map_program_exit_code, map_checker_exit_code


class VerdictMappingTests(unittest.TestCase):
    def test_program_exit_mapping(self):
        self.assertEqual(map_program_exit_code(0), "OK")
        self.assertEqual(map_program_exit_code(124), "Time Limit Exceeded")
        self.assertEqual(map_program_exit_code(137), "Memory Limit Exceeded")
        self.assertIn("Segmentation", map_program_exit_code(139))
        self.assertIn("Segmentation", map_program_exit_code(-11))
        self.assertIn("Abort", map_program_exit_code(134))

    def test_checker_exit_mapping(self):
        self.assertEqual(map_checker_exit_code(0), "Accepted")
        self.assertEqual(map_checker_exit_code(1), "Wrong Answer")
        self.assertEqual(map_checker_exit_code(2), "Presentation Error")
        self.assertEqual(map_checker_exit_code(3), "Checker Error")


if __name__ == "__main__":
    unittest.main()
