import os
import subprocess
import tempfile
import requests

# ⚙️ Local runners cho Python/PyPy
_LOCAL = {
    "python": {
        "filename": "main.py",
        "run": lambda tmp: ["python3", os.path.join(tmp, "main.py")],
    },
    "pypy": {
        "filename": "main.py",
        "run": lambda tmp: ["pypy3", os.path.join(tmp, "main.py")],
    },
}

# 🌐 Piston API để chạy C++/Java (miễn phí)
PISTON_API = "https://emkc.org/api/v2/piston/execute"
PISTON_VERSION = {
    "cpp": "10.2.0",   # GCC
    "java": "15.0.2",
}

def _limit_text(s: str, max_len: int = 1_000_000) -> str:
    """Chặn output quá lớn để tránh bể bộ nhớ."""
    if s is None:
        return ""
    if len(s) > max_len:
        return s[:max_len] + "\n[Output truncated]"
    return s

def run_program(language: str, source_code: str, input_data: str, time_limit: int = 5):
    """
    Trả về tuple (stdout, stderr_or_empty).
    - Python/PyPy: chạy local (nhanh, không cần internet).
    - C++/Java: gọi Piston. Nếu biên dịch lỗi → 'Compilation Error', nếu runtime lỗi → 'Runtime Error'.
    - Hết thời gian → 'Time Limit Exceeded'.
    - Ngôn ngữ chưa hỗ trợ → 'Unsupported language: ...'
    """
    language = (language or "").strip().lower()
    input_data = input_data or ""
    source_code = source_code or ""

    # 🟢 Python/PyPy — chạy local
    if language in _LOCAL:
        cfg = _LOCAL[language]
        try:
            with tempfile.TemporaryDirectory() as tmp:
                src = os.path.join(tmp, cfg["filename"])
                with open(src, "w", encoding="utf-8", newline="\n") as f:
                    f.write(source_code)

                proc = subprocess.run(
                    cfg["run"](tmp),
                    input=input_data,
                    capture_output=True,
                    text=True,
                    timeout=time_limit,
                    env={"PYTHONUNBUFFERED": "1"},
                )
                stdout = _limit_text(proc.stdout)
                stderr = _limit_text(proc.stderr)

                if proc.returncode != 0:
                    # Runtime error cho Python
                    return (f"Runtime Error\n{stderr}".strip(), "")

                return (stdout, "")
        except subprocess.TimeoutExpired:
            return ("Time Limit Exceeded", "")
        except Exception as e:
            # Lỗi nội bộ môi trường
            return (f"Internal Error: {e}", "")

    # 🟣 C++/Java — chạy qua Piston
    if language in ("cpp", "java"):
        try:
            payload = {
                "language": "cpp" if language == "cpp" else "java",
                "version": PISTON_VERSION[language],
                "files": [
                    {
                        "name": f"Main.{ 'cpp' if language == 'cpp' else 'java' }",
                        "content": source_code,
                    }
                ],
                "stdin": input_data,
                # Tăng timeout để an toàn một chút
                "compile_timeout": max(1, time_limit) * 1000,
                "run_timeout": max(1, time_limit) * 1000,
            }
            resp = requests.post(PISTON_API, json=payload, timeout=time_limit + 5)
            if resp.status_code != 200:
                return (f"API Error ({resp.status_code})", "")

            data = resp.json()

            # Piston trả về 2 giai đoạn: compile, run (tùy ngôn ngữ)
            # - Nếu có 'compile' và code != 0 => Compilation Error
            # - Nếu run.code != 0 => Runtime Error
            # - Nếu OK => lấy run.stdout (stderr có thể là warning, bỏ qua nếu code == 0)
            compile_info = data.get("compile", {})
            run_info = data.get("run", {})

            c_code = compile_info.get("code", 0)
            c_stderr = compile_info.get("stderr", "") or ""
            if c_code != 0:
                return ("Compilation Error\n" + _limit_text(c_stderr), "")

            r_code = run_info.get("code", 0)
            r_stdout = _limit_text(run_info.get("stdout", "") or "")
            r_stderr = _limit_text(run_info.get("stderr", "") or "")

            if r_code != 0:
                # Trả stderr để người dùng thấy thông báo lỗi runtime
                return ("Runtime Error\n" + r_stderr, "")

            # Thành công: ưu tiên stdout; warning ở stderr bỏ qua
            return (r_stdout, "")
        except requests.Timeout:
            return ("Time Limit Exceeded", "")
        except Exception as e:
            return (f"API Error: {e}", "")

    # 🔴 Ngôn ngữ khác
    return (f"Unsupported language: {language}", "")
