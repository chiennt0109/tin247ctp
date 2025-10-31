import subprocess, tempfile, os, shutil, requests

PISTON = "https://emkc.org/api/v2/piston/execute"

def _truncate(s, n=2000):
    return (s or "")[:n]

def run_program(language, code, input_data, time_limit=5):
    language = language.lower().strip()

    # ---------------- Python local ----------------
    if language in ("python", "pypy"):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "main.py")
            with open(src, "w") as f:
                f.write(code)
            try:
                p = subprocess.run(
                    ["python3", src] if language=="python" else ["pypy3", src],
                    input=input_data,
                    text=True,
                    capture_output=True,
                    timeout=time_limit
                )
                if p.returncode != 0:
                    return ("Runtime Error", _truncate(p.stderr), "")
                return (p.stdout, "", "")
            except subprocess.TimeoutExpired:
                return ("Time Limit Exceeded", "", "")
            except Exception as e:
                return ("Internal Error", str(e), "")

    # ---------------- C++ local compile ----------------
    if language == "cpp":
        gpp = shutil.which("g++")
        if gpp:
            with tempfile.TemporaryDirectory() as tmp:
                src = os.path.join(tmp, "main.cpp")
                bin = os.path.join(tmp, "a.out")
                with open(src, "w") as f:
                    f.write(code)

                cp = subprocess.run([gpp, src, "-O2", "-std=gnu++17", "-o", bin],
                                    capture_output=True, text=True)

                if cp.returncode != 0:
                    return ("Compilation Error", _truncate(cp.stderr), "")

                try:
                    p = subprocess.run([bin],
                                       input=input_data,
                                       text=True,
                                       capture_output=True,
                                       timeout=time_limit)
                    if p.returncode != 0:
                        return ("Runtime Error", _truncate(p.stderr), "")
                    return (p.stdout, "", "")
                except subprocess.TimeoutExpired:
                    return ("Time Limit Exceeded", "", "")
                except Exception as e:
                    return ("Internal Error", str(e), "")

        # -------- fallback piston API ------------
        try:
            payload = {
                "language": "cpp",
                "version": "10.2.0",
                "files": [{"name": "main.cpp", "content": code}],
                "stdin": input_data
            }
            r = requests.post(PISTON, json=payload, timeout=time_limit + 2)

            if r.text.startswith("<!DOCTYPE"):
                return ("API Error", "", "")

            data = r.json()
            out = data.get("run", {}).get("stdout", "")
            err = data.get("run", {}).get("stderr", "")

            if err.strip():
                return ("Runtime Error", err, "")

            return (out, "", "")
        except Exception as e:
            return ("API Error", str(e), "")

    return ("Unsupported language", f"{language}", "")
