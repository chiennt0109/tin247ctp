from __future__ import annotations

import os
import resource
import subprocess
import time
import tempfile
import math
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


def _build_docker_cmd(bundle: ProgramBundle, memory_limit_mb: int, time_limit: float) -> list[str]:
    cpu_limit_seconds = max(1, math.ceil(float(time_limit)) + 1)
    cmd = [
        "docker",
        "run",
        "--rm",
        "-i",
        "--network=none",
        f"--memory={max(64, int(memory_limit_mb))}m",
        "--cpus=1",
        "--pids-limit=64",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
    ]

    if os.getenv("OJ_DOCKER_USE_ULIMIT", "false").lower() in {"1", "true", "yes"}:
        cmd.extend([
            "--ulimit",
            f"cpu={cpu_limit_seconds}",
            "--ulimit",
            "fsize=16384:16384",
        ])

    cmd.extend([
        "-v",
        f"{bundle.workdir}:/workspace",
        "-w",
        "/workspace",
        DOCKER_IMAGE,
        *_to_container_cmd(bundle),
    ])
    return cmd


def _limit_resources(memory_limit_mb: int):
    memory_bytes = int(memory_limit_mb) * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
    resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
    resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024 * 1024, 16 * 1024 * 1024))


def run_case(bundle: ProgramBundle, input_data: str, time_limit: float, memory_limit_mb: int) -> dict:
    timeout = max(0.1, float(time_limit))
    cmd = _build_docker_cmd(bundle, memory_limit_mb, timeout) if USE_DOCKER else bundle.run_cmd
    # Docker startup overhead should not count as contestant runtime, otherwise
    # short limits can false-positive as TLE for every submission.
    exec_timeout = timeout
    if USE_DOCKER:
        docker_overhead = max(0.0, float(os.getenv("OJ_DOCKER_TIMEOUT_OVERHEAD", "2.0")))
        exec_timeout = timeout + docker_overhead

    # Use explicit stdin/stdout redirection files to avoid blocking stdin issues.
    with tempfile.NamedTemporaryFile(mode="wb", dir=bundle.workdir, delete=False) as fin:
        fin.write((input_data or "").encode("utf-8", errors="ignore"))
        input_file = fin.name

    output_file = os.path.join(bundle.workdir, f"out_{os.path.basename(input_file)}")

    try:
        before_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        start = time.time()
        with open(input_file, "rb") as stdin_fp, open(output_file, "wb") as stdout_fp:
            proc = subprocess.run(
                cmd,
                stdin=stdin_fp,
                stdout=stdout_fp,
                stderr=subprocess.PIPE,
                timeout=exec_timeout,
                cwd=None if USE_DOCKER else bundle.workdir,
                preexec_fn=None if USE_DOCKER else (lambda: _limit_resources(memory_limit_mb)),
                env=os.environ.copy(),
            )
        elapsed = time.time() - start
        after_usage = resource.getrusage(resource.RUSAGE_CHILDREN)

        with open(output_file, "rb") as f:
            stdout_data = f.read()
        stderr_data = proc.stderr or b""

        usage_delta_kb = max(0, int(after_usage.ru_maxrss) - int(before_usage.ru_maxrss))
        memory_kb = usage_delta_kb if usage_delta_kb > 0 else int(after_usage.ru_maxrss or 0)
        return {
            "return_code": proc.returncode,
            "stdout": stdout_data.decode("utf-8", errors="replace"),
            "stderr": stderr_data.decode("utf-8", errors="replace"),
            "time": elapsed,
            "memory_kb": memory_kb,
        }
    except subprocess.TimeoutExpired as exc:
        elapsed = time.time() - start
        return {
            "return_code": 124,
            "stdout": "",
            "stderr": ((exc.stderr or b"").decode("utf-8", errors="replace") if isinstance(exc.stderr, (bytes, bytearray)) else (exc.stderr or "")),
            "time": elapsed,
            "memory_kb": 0,
        }
    except Exception as exc:
        elapsed = time.time() - start if "start" in locals() else 0.0
        return {
            "return_code": 1,
            "stdout": "",
            "stderr": f"runner error: {exc}",
            "time": elapsed,
            "memory_kb": 0,
        }
    finally:
        try:
            os.remove(input_file)
        except Exception:
            pass
        try:
            if os.path.exists(output_file):
                os.remove(output_file)
        except Exception:
            pass
