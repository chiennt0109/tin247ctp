import subprocess, tempfile, os, shutil, requests, json

PISTON_URL = "https://emkc.org/api/v2/piston/execute"

def run_program(language, code, input_data, time_limit=5):
    language = language.lower().strip()

    # ✅ Python local runner
    if language in ("python", "pypy"):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "main.py")
            with open(src, "w") as f: f.write(code)
            try:
                p = subprocess.run(
                    ["python3", src],
                    input=input_data,
                    text=True,
                    capture_output=True,
                    timeout=time_limit
                )
                if p.returncode != 0: 
                    return ("Runtime Error", p.stderr, "")
                return (p.stdout, "", "")
            except subprocess.TimeoutExpired:
                return ("Time Limit Exceeded", "", "")
            except Exception as e:
                return ("Internal Error", str(e), "")

    # ✅ C++ (fallback → Piston API)
    if language == "cpp":
        # ❗ Render không có g++
        # → dùng Piston API
        try:
            payload = {
                "language": "cpp",
                "version": "10.2.0",
                "files": [{"name": "main.cpp", "content": code}],
                "stdin": input_data,
                "run_timeout": time_limit
            }

            r = requests.post(PISTON_URL, json=payload, timeout=time_limit+2)
            data = r.json()

            run = data.get("run", {})
            out = run.get("stdout", "")
            err = run.get("stderr", "")
            code_ret = run.get("code", 0)

            if code_ret != 0:
                return ("Runtime Error", err, "")
            return (out, "", "")
        except requests.Timeout:
            return ("Time Limit Exceeded", "", "")
        except Exception as e:
            return ("API Error", str(e), "")

    return ("Unsupported language", f"{language}", "")
