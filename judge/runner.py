from __future__ import annotations

import os
import resource
import subprocess
import time
from dataclasses import dataclass

DOCKER_IMAGE = os.getenv("OJ_DOCKER_IMAGE", "tin247ctp-runner")
USE_DOCKER = os.getenv("OJ_USE_DOCKER", "true").lower() not in {"0", "false", "no"}


@dataclass
class ProgramBundle:
    language: str
    run_cmd: list[str]
    workdir: str


def compile_submission(language: str, source_code: str, workdir: str) -> tuple[ProgramBundle | None, str]:
    os.makedirs(workdir, exist_ok=True)
    if language == "cpp":
        src = os.path.join(workdir, "main.cpp")
        exe = os.path.join(workdir, "main")
        with open(src, "w", encoding="utf-8") as f:
            f.write(source_code or "")
        proc = subprocess.run(
            ["g++", "main.cpp", "-O2", "-std=c++17", "-o", "main"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=workdir,
            timeout=30,
        )
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
            mapped.append(f"/workspace/{os.path.relpath(arg, bundle.workdir)}")
        else:
            mapped.append(arg)
    return mapped


def _build_docker_cmd(bundle: ProgramBundle, memory_limit_mb: int) -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "--network=none",
        f"--memory={max(64, int(memory_limit_mb))}m",
        "--cpus=1",
        "--pids-limit=64",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "-v",
        f"{bundle.workdir}:/workspace",
        "-w",
        "/workspace",
        DOCKER_IMAGE,
        *_to_container_cmd(bundle),
    ]


def _limit_resources(memory_limit_mb: int):
    memory_bytes = int(memory_limit_mb) * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
    resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
    resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024 * 1024, 16 * 1024 * 1024))


def run_case(bundle: ProgramBundle, input_data: str, time_limit: float, memory_limit_mb: int) -> dict:
    t0 = time.perf_counter()
    timeout = max(0.1, float(time_limit))
    cmd = _build_docker_cmd(bundle, memory_limit_mb) if USE_DOCKER else bundle.run_cmd

    try:
        proc = subprocess.run(
            cmd,
            input=input_data or "",
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            cwd=None if USE_DOCKER else bundle.workdir,
            preexec_fn=None if USE_DOCKER else (lambda: _limit_resources(memory_limit_mb)),
            env={"PATH": os.getenv("PATH", "")},
        )
        elapsed = time.perf_counter() - t0
        memory_kb = max(0, memory_limit_mb * 1024 if proc.returncode == 137 else 0)
        return {
            "return_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "time": elapsed,
            "memory_kb": memory_kb,
        }
    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - t0
        return {
            "return_code": 124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "time": elapsed,
            "memory_kb": 0,
        }
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        return {
            "return_code": 1,
            "stdout": "",
            "stderr": f"runner error: {exc}",
            "time": elapsed,
            "memory_kb": 0,
        }
