import os
import tempfile
from contextlib import contextmanager

TMP_ROOT = "/dev/shm/judge_tmp"


@contextmanager
def checker_tempfiles(input_data: str, output_data: str, expected_data: str):
    os.makedirs(TMP_ROOT, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="sj_", dir=TMP_ROOT) as td:
        in_path = os.path.join(td, "input.txt")
        out_path = os.path.join(td, "output.txt")
        exp_path = os.path.join(td, "expected.txt")
        for p, c in ((in_path, input_data), (out_path, output_data), (exp_path, expected_data)):
            with open(p, "w", encoding="utf-8") as f:
                f.write(c or "")
        yield in_path, out_path, exp_path
