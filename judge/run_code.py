import subprocess, tempfile, os, requests

# Cấu hình cho các ngôn ngữ chạy local (chỉ Python/PyPy)
LOCAL_COMPILERS = {
    'python': {
        'src': 'main.py',
        'compile': None,
        'run': lambda tmp: ["python3", os.path.join(tmp, "main.py")],
    },
    'pypy': {
        'src': 'main.py',
        'compile': None,
        'run': lambda tmp: ["pypy3", os.path.join(tmp, "main.py")],
    },
}

# API chấm code miễn phí (Piston)
PISTON_API = "https://emkc.org/api/v2/piston/execute"


def run_program(language: str, source_code: str, input_data: str, time_limit: int = 5):
    """
    Hàm chạy/chấm code cho nhiều ngôn ngữ.
    - Python, PyPy: chạy local.
    - C++, Java: gọi Piston API miễn phí.
    """

    # 🟢 Nếu dùng Python hoặc PyPy: chạy trực tiếp local
    if language in LOCAL_COMPILERS:
        cfg = LOCAL_COMPILERS[language]
        with tempfile.TemporaryDirectory() as tmp:
            src_path = os.path.join(tmp, cfg['src'])
            with open(src_path, 'w') as f:
                f.write(source_code)
            try:
                r = subprocess.run(
                    cfg['run'](tmp),
                    input=input_data,
                    capture_output=True,
                    text=True,
                    timeout=time_limit,
                    env={"PYTHONUNBUFFERED": "1"},
                )
                if r.returncode != 0:
                    return ("Runtime Error:\n" + r.stderr, 0.0)
                return (r.stdout, r.stderr)
            except subprocess.TimeoutExpired:
                return ("Time Limit Exceeded", 0.0)
            except Exception as e:
                return (f"Internal Error: {e}", 0.0)

    # 🟣 Nếu là C++ hoặc Java: gọi Piston API
    elif language in ["cpp", "java"]:
        try:
            payload = {
                "language": "cpp" if language == "cpp" else "java",
                "version": "10.2.0" if language == "cpp" else "15.0.2",
                "files": [{"name": f"main.{ 'cpp' if language == 'cpp' else 'java' }", "content": source_code}],
                "stdin": input_data
            }
            resp = requests.post(PISTON_API, json=payload, timeout=time_limit + 3)
            data = resp.json()

            if resp.status_code != 200:
                return (f"API Error ({resp.status_code})", 0.0)

            if "run" not in data:
                return (f"Invalid API Response: {data}", 0.0)

            run = data["run"]
            stdout, stderr = run.get("stdout", ""), run.get("stderr", "")
            if stderr.strip():
                return ("Runtime Error:\n" + stderr, 0.0)
            return (stdout, 0.0)
        except requests.Timeout:
            return ("Time Limit Exceeded", 0.0)
        except Exception as e:
            return (f"API Error: {e}", 0.0)

    # 🔴 Ngôn ngữ khác chưa hỗ trợ
    else:
        return (f"Unsupported language: {language}", 0.0)
