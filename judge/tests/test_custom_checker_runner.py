import os
import stat
import unittest
from pathlib import Path

from judge.checkers import run_custom_checker


class CustomCheckerRunnerTests(unittest.TestCase):
    def setUp(self):
        self.problem_code = "_t_custom_checker"
        self.dir = Path(f"/srv/judge/testcases/{self.problem_code}")
        self.dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        checker = self.dir / "checker"
        if checker.exists():
            checker.unlink()

    def _write_checker(self, body: str):
        checker = self.dir / "checker"
        checker.write_text(body, encoding="utf-8")
        checker.chmod(checker.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def test_default_argument_order_in_out_exp(self):
        self._write_checker(
            "#!/usr/bin/env bash\n"
            "in=$1; out=$2; exp=$3\n"
            "test \"$(cat $out)\" = \"OUT\" && test \"$(cat $exp)\" = \"EXP\"\n"
        )
        res = run_custom_checker(self.problem_code, "IN", "OUT", "EXP")
        self.assertEqual(res["return_code"], 0)

    def test_configurable_argument_order_in_exp_out(self):
        self._write_checker(
            "#!/usr/bin/env bash\n"
            "in=$1; exp=$2; out=$3\n"
            "test \"$(cat $out)\" = \"OUT\" && test \"$(cat $exp)\" = \"EXP\"\n"
        )
        res = run_custom_checker(self.problem_code, "IN", "OUT", "EXP", config="custom_order=in_exp_out")
        self.assertEqual(res["return_code"], 0)


if __name__ == "__main__":
    unittest.main()
