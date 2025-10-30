# path: judge/run_code.py
import os, subprocess, tempfile, requests

_LOCAL = {
    "python": {
        "file": "main.py",
        "run": lambda tmp: ["python3", os.path.join(tmp, "main.py")],
    },
    "pypy": {
        "file": "main.py",
        "run": lambda tmp: ["pypy3", os.path.join(tmp, "main.py")],
    },
}

PISTON_API = "https://emkc.org/api/v2/piston/execute"
PISTON_VERSION = {
    "cpp": "10.2.0",
    "java": "15.0.2",
}

def _cut(s, limit=1_000_000):
    if not s: return ""
    return s if len(s) <= limit else s[:limit] + "\n[output truncated]"

def run_program(language, source_code, input_data, time_limit=5):
    language = (language or "").lower().strip()
    source_code = source_code or ""
    input_data = input_data or ""

    # ✅ Python / PyPy chạy local
    if language in _LOCAL:
        cfg = _LOCAL[language]
        try:
            with tempfile.TemporaryDirectory() as tmp:
                src = os.path.join(tmp, cfg["file"])
                with open(src, "w") as f: f.write(source_code)

                proc = subprocess.run(
                    cfg["run"](tmp),
                    input=input_data,
                    capture_output=True,
                    text=True,
                    timeout=time_limit
                )
                if proc.returncode != 0:
                    return (f"Runtime Error\n{_cut(proc.stderr)}", "")
                return (_cut(proc.stdout), "")
        except subprocess.TimeoutExpired:
            return ("Time Limit Exceeded", "")
        except Exception as e:
            return (f"Internal Error: {e}", "")

    # ✅ C++ / Java dùng API miễn phí
    if language in ("cpp", "java"):
        try:
            payload = {
                "language": language,
                "version": PISTON_VERSION[language],
                "files": [{"name": f"main.{language}", "content": source_code}],
                "stdin": input_data,
            }
            r = requests.post(PISTON_API, json=payload, timeout=time_limit + 4)
            data = r.json()

            if r.status_code != 200:
                return (f"API Error ({r.status_code})", "")

            if data.get("compile", {}).get("code"):
                return ("Compilation Error\n" + _cut(data["compile"]["stderr"]), "")

            run = data.get("run", {})
            if run.get("code") != 0:
                return ("Runtime Error\n" + _cut(run.get("stderr", "")), "")

            return (_cut(run.get("stdout", "")), "")
        except requests.Timeout:
            return ("Time Limit Exceeded", "")
        except Exception as e:
            return (f"API Error: {e}", "")

    return (f"Unsupported language: {language}", "")
