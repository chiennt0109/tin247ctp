import os
import stat
import time
import unittest
from pathlib import Path

from judge.special_judge.runner import run_special_judge
from judge.special_judge.compiler import CACHE_ROOT


class SpecialJudgeTests(unittest.TestCase):
    def setUp(self):
        self.problem_code = "_t_sj"
        self.tc_dir = Path(f"/srv/judge/testcases/{self.problem_code}")
        self.tc_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir = Path(f"{CACHE_ROOT}/{self.problem_code}")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        for p in [self.tc_dir / "checker", self.tc_dir / "checker.cpp", self.tc_dir / "checker.py", self.cache_dir / "checker", self.cache_dir / "checker_py_runner.sh"]:
            if p.exists():
                p.unlink()

    def test_permutation(self):
        res = run_special_judge(self.problem_code, "permutation", "5", "1 3 2 5 4", "")
        self.assertEqual(res["return_code"], 0)

    def test_set_compare(self):
        res = run_special_judge(self.problem_code, "set_compare", "", "b a", "a b")
        self.assertEqual(res["return_code"], 0)

    def test_numeric_tolerance(self):
        res = run_special_judge(self.problem_code, "numeric_tolerance", "", "3.14", "3.1400004", "eps=0.001")
        self.assertEqual(res["return_code"], 0)

    def test_euler_path(self):
        # n=3, m=2, edges (1,2),(2,3)
        res = run_special_judge(self.problem_code, "euler_path", "3 2 1 2 2 3", "1 2 3", "")
        self.assertEqual(res["return_code"], 0)


    def test_euler_path_zero_based(self):
        res = run_special_judge(self.problem_code, "euler_path", "3 2 0 1 1 2", "0 1 2", "")
        self.assertEqual(res["return_code"], 0)

    def test_graph_path(self):
        res = run_special_judge(self.problem_code, "graph_path", "4 3 1 2 2 3 3 4", "1 2 3 4", "")
        self.assertEqual(res["return_code"], 0)

    def test_tree(self):
        res = run_special_judge(self.problem_code, "tree", "4", "1 2 2 3 3 4", "")
        self.assertEqual(res["return_code"], 0)

    def test_custom_checker_cpp_and_cache(self):
        cpp = self.tc_dir / "checker.cpp"
        cpp.write_text(
            '#include <bits/stdc++.h>\n'
            'using namespace std;\n'
            'int main(int argc,char**argv){\n'
            ' if(argc<4) return 3;\n'
            ' ifstream out(argv[2]), exp(argv[3]);\n'
            ' string a,b; getline(out,a); getline(exp,b);\n'
            ' return a==b?0:1;\n'
            '}\n',
            encoding="utf-8",
        )
        res1 = run_special_judge(self.problem_code, "custom", "IN", "X", "X")
        self.assertEqual(res1["return_code"], 0)
        bin_path = self.cache_dir / "checker"
        self.assertTrue(bin_path.exists())
        m1 = bin_path.stat().st_mtime
        time.sleep(0.1)
        res2 = run_special_judge(self.problem_code, "custom", "IN", "Y", "Y")
        self.assertEqual(res2["return_code"], 0)
        m2 = bin_path.stat().st_mtime
        self.assertEqual(m1, m2)


if __name__ == "__main__":
    unittest.main()
