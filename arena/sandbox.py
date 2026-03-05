# arena/sandbox.py
import os
import tempfile
import subprocess


class SandboxError(Exception):
    pass


def run_bot_in_sandbox(language: str, source_code: str, stdin_data: str, time_limit: float = 1.0) -> str:
    """
    Chạy bot trong "sandbox".
    - Hiện tại: chạy local bằng subprocess (dùng cho admin).
    - Sau này: bạn có thể thay thế bằng call sang hệ thống judge Docker.
    """
    stdin_bytes = stdin_data.encode("utf-8")

    with tempfile.TemporaryDirectory() as tmpdir:
        if language == "cpp":
            src_path = os.path.join(tmpdir, "main.cpp")
            exe_path = os.path.join(tmpdir, "main.out")
            with open(src_path, "w", encoding="utf-8") as f:
                f.write(source_code)

            # compile
            comp = subprocess.run(
                ["g++", "-O2", "-std=c++17", src_path, "-o", exe_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
            )
            if comp.returncode != 0:
                raise SandboxError("Compile error:\n" + comp.stderr.decode("utf-8", errors="ignore"))

            # run
            proc = subprocess.run(
                [exe_path],
                input=stdin_bytes,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=time_limit,
            )
            if proc.returncode != 0:
                raise SandboxError("Runtime error:\n" + proc.stderr.decode("utf-8", errors="ignore"))

            return proc.stdout.decode("utf-8", errors="ignore")

        elif language == "py":
            src_path = os.path.join(tmpdir, "main.py")
            with open(src_path, "w", encoding="utf-8") as f:
                f.write(source_code)

            proc = subprocess.run(
                ["python3", src_path],
                input=stdin_bytes,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=time_limit,
            )
            if proc.returncode != 0:
                raise SandboxError("Runtime error:\n" + proc.stderr.decode("utf-8", errors="ignore"))

            return proc.stdout.decode("utf-8", errors="ignore")

        else:
            raise SandboxError(f"Ngôn ngữ không hỗ trợ: {language}")

    # Nếu muốn dùng Docker sandbox hiện tại:
    # - Import hàm chạy sandbox của bạn ở đây, ví dụ:
    # from submissions.sandbox import run_in_sandbox
    # và thay logic compile+run bên trên bằng gọi run_in_sandbox(...)
