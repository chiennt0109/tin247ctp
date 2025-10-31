import subprocess, tempfile, os, shutil, requests

PISTON = "https://emkc.org/api/v2/piston/execute"

def _safe(s):
    if s is None:
        return ""
    return str(s)[:5000]  # avoid huge logs

def run_program(language, code, input_data, time_limit=4):
    language = language.lower().strip()

    # ✅ PYTHON / PYPY local execution
    if language in ("python", "pypy"):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "main.py")
            with open(src, "w") as f:
                f.write(code)

            try:
                p = subprocess.run(
                    ["python3", src] if language == "python" else ["pypy3", src],
                    input=input_data,
                    text=True,
                    capture_output=True,
                    timeout=time_limit
                )
                if p.returncode != 0:
                    return ("Runtime Error:\n" + _safe(p.stderr), _safe(p.stderr))
                return (_safe(p.stdout), _safe(p.stderr))
            except subprocess.TimeoutExpired:
                return ("Time Limit Exceeded", "")
            except Exception as e:
                return (f"Internal Error: {e}", "")

    # ✅ C++ compile & run (LOCAL if available)
    if language == "cpp":
        gxx = shutil.which("g++")

        if gxx:
            with tempfile.TemporaryDirectory() as tmp:
                src = os.path.join(tmp, "main.cpp")
                out = os.path.join(tmp, "a.out")
                with open(src, "w") as f:
                    f.write(code)

                compile_p = subprocess.run([gxx, src, "-O2", "-std=gnu++17", "-o", out],
                                           capture_output=True, text=True)

                if compile_p.returncode != 0:
                    return ("Compilation Error:\n" + _safe(compile_p.stderr), _safe(compile_p.stderr))

                try:
                    run_p = subprocess.run([out], input=input_data, text=True,
                                           capture_output=True, timeout=time_limit)
                    if run_p.returncode != 0:
                        return ("Runtime Error:\n" + _safe(run_p.stderr), _safe(run_p.stderr))
                    return (_safe(run_p.stdout), _safe(run_p.stderr))
                except subprocess.TimeoutExpired:
                    return ("Time Limit Exceeded", "")
                except Exception as e:
                    return (f"Internal Error: {e}", "")

        # ✅ If no g++ → fallback to PISTON
        try:
            payload = {
                "language": "cpp",
                "version": "10.2.0",
                "files": [{"name": "main.cpp", "content": code}],
                "stdin": input_data
            }
            r = requests.post(PISTON, json=payload, timeout=time_limit + 2)

            if r.text.startswith("<!DOCTYPE"):
                return ("API Error", "")

            data = r.json()
            out = data.get("run", {}).get("stdout", "")
            err = data.get("run", {}).get("stderr", "")

            if err.strip():
                return ("Runtime Error:\n" + _safe(err), _safe(err))

            return (_safe(out), _safe(err))

        except requests.Timeout:
            return ("Time Limit Exceeded", "")
        except Exception as e:
            return (f"API Error: {e}", "")

    return ("Unsupported language", "")
