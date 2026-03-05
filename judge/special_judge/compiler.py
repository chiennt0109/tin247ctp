import os
import subprocess

CACHE_ROOT = "/srv/judge/checker_cache"
TESTCASE_ROOT = "/srv/judge/testcases"


def ensure_custom_checker(problem_code: str):
    src_dir = os.path.join(TESTCASE_ROOT, problem_code)
    cache_dir = os.path.join(CACHE_ROOT, problem_code)
    os.makedirs(cache_dir, exist_ok=True)

    checker_bin_src = os.path.join(src_dir, "checker")
    checker_cpp = os.path.join(src_dir, "checker.cpp")
    checker_py = os.path.join(src_dir, "checker.py")
    checker_bin_cache = os.path.join(cache_dir, "checker")

    if os.path.exists(checker_bin_src):
        return checker_bin_src, ""

    if os.path.exists(checker_py):
        runner = os.path.join(cache_dir, "checker_py_runner.sh")
        with open(runner, "w", encoding="utf-8") as f:
            f.write("#!/usr/bin/env bash\nexec python3 \"%s\" \"$@\"\n" % checker_py)
        os.chmod(runner, 0o755)
        return runner, ""

    if not os.path.exists(checker_cpp):
        return None, f"No checker/checker.cpp/checker.py for {problem_code}"

    need_compile = True
    if os.path.exists(checker_bin_cache):
        need_compile = os.path.getmtime(checker_cpp) > os.path.getmtime(checker_bin_cache)

    if need_compile:
        proc = subprocess.run(
            ["g++", checker_cpp, "-O2", "-std=c++17", "-o", checker_bin_cache],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
        )
        if proc.returncode != 0:
            return None, f"compile checker.cpp failed: {proc.stderr}"
        os.chmod(checker_bin_cache, 0o755)

    return checker_bin_cache, ""
