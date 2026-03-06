from __future__ import annotations

import os
import subprocess
import tempfile
import time
from dataclasses import dataclass

DOCKER_IMAGE = os.getenv("OJ_DOCKER_IMAGE", "tin247ctp-runner")
USE_DOCKER = os.getenv("OJ_USE_DOCKER", "true").lower() not in {"0", "false", "no"}


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


def _to_container_cmd(bundle: ProgramBundle) -> list[str]:
    mapped = []
    for arg in bundle.run_cmd:
        if isinstance(arg, str) and arg.startswith(bundle.workdir):
            rel = os.path.relpath(arg, bundle.workdir)
            mapped.append(f"/workspace/{rel}")
        else:
            mapped.append(arg)
    return mapped


def _build_docker_cmd(bundle: ProgramBundle) -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "--network=none",
        "--memory=512m",
        "--cpus=1",
        "--pids-limit=64",
        "--read-only",
        "-v",
        f"{bundle.workdir}:/workspace",
        "-w",
        "/workspace",
        DOCKER_IMAGE,
        *_to_container_cmd(bundle),
    ]


def run_case(bundle: ProgramBundle, input_data: str, time_limit: float) -> dict:
    t0 = time.perf_counter()
    timeout = max(0.1, float(time_limit))
    cmd = _build_docker_cmd(bundle) if USE_DOCKER else bundle.run_cmd

    try:
        proc = subprocess.run(
            cmd,
            input=input_data or "",
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            cwd=None if USE_DOCKER else bundle.workdir,
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
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        return {
            "return_code": 1,
            "stdout": "",
            "stderr": f"runner error: {exc}",
            "time": elapsed,
        }
