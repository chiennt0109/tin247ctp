from __future__ import annotations

import os
import resource
import subprocess
import time
import math
import shlex
from dataclasses import dataclass

DOCKER_IMAGE = os.getenv("OJ_DOCKER_IMAGE", "tin247ctp-runner")
USE_DOCKER = os.getenv("OJ_USE_DOCKER", "true").lower() not in {"0", "false", "no"}
DOCKER_RUN_CPUS = os.getenv("OJ_DOCKER_CPUS", "0.5")
DOCKER_COMPILE_CPUS = os.getenv("OJ_DOCKER_COMPILE_CPUS", DOCKER_RUN_CPUS)


@dataclass
class ProgramBundle:
    language: str
    run_cmd: list[str]
    workdir: str


def _get_docker_image(bundle: ProgramBundle):
    if bundle.language == "cpp":
        return "judge-cpp"
    if bundle.language in ("python", "pypy"):
        return "judge-py"
    if bundle.language == "java":
        return "judge-java"
    return os.getenv("OJ_DOCKER_IMAGE", "judge-cpp")


def _docker_user_args() -> list[str]:
    """Run container process as the same host UID/GID to avoid bind-mount write denial."""
    uid = os.getuid()
    gid = os.getgid()
    return ["--user", f"{uid}:{gid}"]


def compile_submission(language: str, source_code: str, workdir: str) -> tuple[ProgramBundle | None, str]:
    os.makedirs(workdir, exist_ok=True)
    if language == "cpp":
        src = os.path.join(workdir, "main.cpp")
        exe = os.path.join(workdir, "main")
        with open(src, "w", encoding="utf-8") as f:
            f.write(source_code or "")
        os.chmod(src, 0o644)
        if USE_DOCKER:
            compile_cmd = [
                "docker",
                "run",
                "--rm",
                "--network=none",
                "--cpus",
                str(DOCKER_COMPILE_CPUS),
                *_docker_user_args(),
                "-v",
                f"{workdir}:/workspace",
                "-w",
                "/workspace",
                _get_docker_image(ProgramBundle(language="cpp", run_cmd=[], workdir=workdir)),
                "g++",
                "main.cpp",
                "-O2",
                "-std=c++17",
                "-o",
                "main",
            ]
            proc = subprocess.run(
                compile_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )
        else:
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
        os.chmod(src, 0o644)
        interp = "python3" if language == "python" else "pypy3"
        return ProgramBundle(language=language, run_cmd=[interp, src], workdir=workdir), ""

    return None, f"Unsupported language: {language}"


def _to_container_cmd(bundle: ProgramBundle) -> list[str]:
    mapped = []
    for arg in bundle.run_cmd:
        if isinstance(arg, str) and arg.startswith(bundle.workdir):
            mapped.append(f"./{os.path.relpath(arg, bundle.workdir)}")
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
        *_docker_user_args(),
        f"--memory={max(64, int(memory_limit_mb))}m",
        f"--cpus={DOCKER_RUN_CPUS}",
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

    container_cmd = _to_container_cmd(bundle)
    shell_cmd = shlex.join(container_cmd)
    cmd.extend([
        "-v",
        f"{bundle.workdir}:/workspace",
        "-w",
        "/workspace",
        _get_docker_image(bundle),
        "/bin/sh",
        "-c",
        shell_cmd,
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

    # Use explicit files inside workspace to ensure they are visible in Docker mount.
    input_file = os.path.join(bundle.workdir, "input.txt")
    output_file = os.path.join(bundle.workdir, "output.txt")
    with open(input_file, "wb") as fin:
        fin.write((input_data or "").encode("utf-8", errors="ignore"))

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
        normalized_rc = 125 if proc.returncode == 127 else proc.returncode
        return {
            "return_code": normalized_rc,
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
