"""Docker-only, bounded runner for the interactive playground.

This service is intentionally separate from ``judge.runner`` so changes here can
never alter the official submission/judging pipeline.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path


CPP_IMAGE = os.getenv("PLAYGROUND_CPP_IMAGE", "judge-cpp")
PYTHON_IMAGE = os.getenv("PLAYGROUND_PYTHON_IMAGE", "judge-py")
PLAYGROUND_ROOT = os.getenv("PLAYGROUND_ROOT", "/tmp/tin247_playground")
OUTPUT_LIMIT = int(os.getenv("PLAYGROUND_OUTPUT_LIMIT", str(1024 * 1024)))
COMPILE_OUTPUT_LIMIT = int(os.getenv("PLAYGROUND_COMPILE_OUTPUT_LIMIT", str(256 * 1024)))
DOCKER_TIMEOUT_OVERHEAD = float(os.getenv("PLAYGROUND_DOCKER_OVERHEAD", "3"))


class PlaygroundSystemError(RuntimeError):
    pass


@dataclass
class PlaygroundResult:
    ok: bool = True
    status: str = "OK"
    stdout: str = ""
    stderr: str = ""
    compile_output: str = ""
    time_ms: int = 0
    memory_kb: int = 0
    message: str = ""
    detail: str = ""

    def payload(self) -> dict:
        return asdict(self)


def _image_for(language: str) -> str:
    return CPP_IMAGE if language == "cpp17" else PYTHON_IMAGE


def normalize_language(language: str) -> str | None:
    value = (language or "").strip().lower()
    if value in {"cpp", "cpp17", "c++", "c++17"}:
        return "cpp17"
    if value in {"python", "python3", "py"}:
        return "python"
    return None


def runner_health(language: str | None = None) -> tuple[bool, str]:
    if not shutil.which("docker"):
        return False, "Docker CLI not found in PATH"
    try:
        probe = subprocess.run(
            ["docker", "info"], capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"Cannot execute Docker CLI: {exc}"
    if probe.returncode:
        detail = (probe.stderr or probe.stdout).strip()
        return False, f"Docker daemon is not accessible: {detail[:500]}"
    images = (_image_for(language),) if language else (CPP_IMAGE, PYTHON_IMAGE)
    for image in images:
        try:
            probe = subprocess.run(
                ["docker", "image", "inspect", image], capture_output=True, text=True, timeout=10
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return False, f"Cannot inspect Docker image {image}: {exc}"
        if probe.returncode:
            return False, f"Docker image {image} not found"
    return True, "ready"


def _read_limited(path: Path, limit: int) -> str:
    with path.open("rb") as stream:
        return stream.read(limit).decode("utf-8", errors="replace")


def _container_base(name: str, memory_mb: int, cpus: str = "0.5") -> list[str]:
    return [
        "docker", "run", "--rm", "--name", name, "--network=none",
        f"--memory={memory_mb}m", f"--cpus={cpus}", "--pids-limit=64",
        "--cap-drop=ALL", "--security-opt=no-new-privileges", "--read-only",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
        "--user", f"{os.getuid()}:{os.getgid()}",
    ]


def _kill_container(name: str) -> None:
    try:
        subprocess.run(
            ["docker", "rm", "-f", name], stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def _execute(cmd: list[str], workspace: Path, timeout: float, output_limit: int) -> dict:
    stdout_path, stderr_path = workspace / "stdout.txt", workspace / "stderr.txt"
    started = time.monotonic()
    name = cmd[cmd.index("--name") + 1]
    timed_out = output_limited = False
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        try:
            process = subprocess.Popen(cmd, stdout=stdout, stderr=stderr)
        except (FileNotFoundError, PermissionError) as exc:
            raise PlaygroundSystemError(str(exc)) from exc
        try:
            while process.poll() is None:
                elapsed = time.monotonic() - started
                if elapsed > timeout:
                    timed_out = True
                    _kill_container(name)
                    break
                if stdout_path.stat().st_size + stderr_path.stat().st_size > output_limit:
                    output_limited = True
                    _kill_container(name)
                    break
                time.sleep(0.025)
            if stdout_path.stat().st_size + stderr_path.stat().st_size > output_limit:
                output_limited = True
            try:
                return_code = process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                return_code = process.wait(timeout=2)
        finally:
            if timed_out or output_limited:
                _kill_container(name)
    return {
        "return_code": return_code,
        "stdout": _read_limited(stdout_path, output_limit),
        "stderr": _read_limited(stderr_path, output_limit),
        "elapsed": time.monotonic() - started,
        "timed_out": timed_out,
        "output_limited": output_limited,
    }


def run_playground(language: str, source: str, stdin: str, *, time_limit: float = 2,
                   memory_mb: int = 256) -> PlaygroundResult:
    language = normalize_language(language)
    if language is None:
        return PlaygroundResult(ok=False, status="BAD_REQUEST", message="Unsupported language")

    healthy, detail = runner_health(language)
    if not healthy:
        raise PlaygroundSystemError(detail)

    os.makedirs(PLAYGROUND_ROOT, mode=0o700, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix="run_", dir=PLAYGROUND_ROOT))
    os.chmod(workspace, 0o755)
    try:
        (workspace / "input.txt").write_text(stdin or "", encoding="utf-8")
        if language == "cpp17":
            (workspace / "main.cpp").write_text(source, encoding="utf-8")
            os.chmod(workspace / "main.cpp", 0o644)
            compile_name = f"playground-compile-{uuid.uuid4().hex[:12]}"
            compile_cmd = _container_base(compile_name, 512) + [
                "-v", f"{workspace}:/workspace:rw", "-w", "/workspace", CPP_IMAGE,
                "g++", "main.cpp", "-O2", "-std=c++17", "-o", "main",
            ]
            compiled = _execute(compile_cmd, workspace, 30 + DOCKER_TIMEOUT_OVERHEAD, COMPILE_OUTPUT_LIMIT)
            if compiled["return_code"] == 125:
                raise PlaygroundSystemError((compiled["stderr"] or "Docker compile container failed")[:500])
            compile_output = (compiled["stdout"] + compiled["stderr"])[:COMPILE_OUTPUT_LIMIT]
            if compiled["timed_out"]:
                return PlaygroundResult(status="CE", compile_output="Compiler timeout")
            if compiled["output_limited"]:
                return PlaygroundResult(status="CE", compile_output="Compiler output limit exceeded")
            if compiled["return_code"] != 0:
                return PlaygroundResult(status="CE", compile_output=compile_output)
            os.chmod(workspace / "main", 0o755)
            command = ["./main"]
        else:
            (workspace / "main.py").write_text(source, encoding="utf-8")
            os.chmod(workspace / "main.py", 0o644)
            command = ["python3", "main.py"]

        run_name = f"playground-run-{uuid.uuid4().hex[:12]}"
        run_cmd = _container_base(run_name, memory_mb) + [
            "-i", "-v", f"{workspace}:/workspace:ro", "-w", "/workspace",
            _image_for(language), "/bin/sh", "-c", "exec \"$@\" < input.txt", "runner", *command,
        ]
        result = _execute(run_cmd, workspace, time_limit + DOCKER_TIMEOUT_OVERHEAD, OUTPUT_LIMIT)
        if result["return_code"] == 125:
            raise PlaygroundSystemError((result["stderr"] or "Docker run container failed")[:500])
        # Wall-clock time includes the small container startup cost but remains
        # truthful and monotonic; do not subtract a fixed value (which produced
        # misleading 0 ms results for normal programs).
        time_ms = max(0, int(result["elapsed"] * 1000))
        if result["output_limited"]:
            status = "OUTPUT_LIMIT"
        elif result["timed_out"]:
            status = "TLE"
        elif result["return_code"] in {137, 139}:
            status = "MLE" if result["return_code"] == 137 else "RE"
        elif result["return_code"] != 0:
            status = "RE"
        else:
            status = "OK"
        return PlaygroundResult(
            status=status, stdout=result["stdout"], stderr=result["stderr"],
            time_ms=time_ms, memory_kb=0,
        )
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
