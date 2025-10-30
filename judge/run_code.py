import subprocess, tempfile, os, requests, json

# API chạy code miễn phí
PISTON_API = "https://emkc.org/api/v2/piston/execute"

LOCAL_COMPILERS = {
    'python': {
        'src': 'main.py',
        'run': lambda tmp: ["python3", os.path.join(tmp, "main.py")],
    },
    'pypy': {
        'src': 'main.py',
        'run': lambda tmp: ["pypy3", os.path.join(tmp, "main.py")],
    },
}

def run_program(language: str, source_code: str, input_data: str, time_limit: int = 5):
    # ✅ Python / PyPy chạy local
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
                    timeout=time_limit
                )
                if r.returncode != 0:
                    return ("Runtime Error:\n" + r.stderr, "")
                return (r.stdout, "")
            except subprocess.TimeoutExpired:
                return ("Time Limit Exceeded", "")
            except Exception as e:
                return (f"Internal Error: {e}", "")

    # ✅ C++ / Java: gửi API chấm
    elif language in ["cpp", "java"]:
        try:
            payload = {
                "language": "cpp" if language == "cpp" else "java",
                "version": "10.2.0" if language == "cpp" else "15.0.2",
                "files": [
                    {"name": "main.cpp" if language == "cpp" else "Main.java",
                     "content": source_code}
                ],
                "stdin": input_data
            }

            resp = requests.post(PISTON_API, json=payload, timeout=time_limit+2)
            data = resp.json()

            run = data.get("run", {})
            stdout = run.get("stdout", "").strip()
            stderr = run.get("stderr", "").strip()

            if stderr:
                return (f"Runtime Error:\n{stderr}", "")

            return (stdout, "")
        except requests.Timeout:
            return ("Time Limit Exceeded", "")
        except Exception as e:
            return (f"API Error: {e}", "")

    return (f"Unsupported language: {language}", "")
