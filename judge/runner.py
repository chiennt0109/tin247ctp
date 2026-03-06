from __future__ import annotations

import os
import subprocess
import tempfile
import time
from dataclasses import dataclass


@dataclass
class ProgramBundle:
    language: str
    run_cmd: list[str]
    workdir: str


def compile_submission(language: str, source_code: str) -> tuple[ProgramBundle | None, str]:
    workdir = tempfile.mkdtemp(prefix="judge_sub_")
    if language == "cpp":
        src = os.path.join(workdir, "main.cpp")
        exe = os.path.join(workdir, "main")
        with open(src, "w", encoding="utf-8") as f:
            f.write(source_code or "")
        proc = subprocess.run(["g++", "-std=c++17", "-O2", src, "-o", exe], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            return None, proc.stderr
        os.chmod(exe, 0o755)
        return ProgramBundle(language=language, run_cmd=[exe], workdir=workdir), ""

    if language in ("python", "pypy"):
        src = os.path.join(workdir, "main.py")
        with open(src, "w", encoding="utf-8") as f:
            f.write(source_code or "")
        interp = "python3" if language == "python" else "pypy3"
        return ProgramBundle(language=language, run_cmd=[interp, src], workdir=workdir), ""

    return None, f"Unsupported language: {language}"


def run_case(bundle: ProgramBundle, input_data: str, time_limit: float) -> dict:
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            bundle.run_cmd,
            input=input_data or "",
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=max(0.1, float(time_limit)),
            cwd=bundle.workdir,
        )
        elapsed = time.perf_counter() - t0
        return {
            "return_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "time": elapsed,
        }
    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - t0
        return {
            "return_code": 124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "time": elapsed,
        }
