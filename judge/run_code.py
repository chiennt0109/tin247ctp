# path: judge/run_code.py
import subprocess, tempfile, os, shutil, requests

PISTON = "https://emkc.org/api/v2/piston/execute"

def safe(x):
    return "" if x is None else str(x)

def run_program(lang, code, stdin, time_limit=4):
    lang = lang.lower().strip()

    # -------------------------------- PYTHON LOCAL --------------------------------
    if lang in ("python", "pypy"):
        with tempfile.TemporaryDirectory() as tmp:
            src = f"{tmp}/main.py"
            open(src, "w").write(code)

            try:
                p = subprocess.run(
                    ["python3", src],
                    input=stdin, text=True,
                    capture_output=True, timeout=time_limit
                )
                if p.returncode != 0:
                    return (f"Runtime Error:\n{safe(p.stderr)}", safe(p.stderr))
                return (safe(p.stdout), safe(p.stderr))
            except subprocess.TimeoutExpired:
                return ("Time Limit Exceeded", "")
            except Exception as e:
                return (f"Internal Error: {e}", "")

    # -------------------------------- C++ LOCAL / FALLBACK --------------------------------
    if lang == "cpp":
        gpp = shutil.which("g++")
        if gpp:
            with tempfile.TemporaryDirectory() as tmp:
                src = f"{tmp}/main.cpp"
                exe = f"{tmp}/a.out"
                open(src, "w").write(code)

                cp = subprocess.run([gpp, src, "-O2", "-std=gnu++17", "-o", exe],
                                    capture_output=True, text=True)

                if cp.returncode != 0:
                    return (f"Compilation Error:\n{safe(cp.stderr)}", safe(cp.stderr))

                try:
                    run = subprocess.run(
                        [exe], input=stdin, text=True,
                        capture_output=True, timeout=time_limit
                    )

                    if run.returncode != 0:
                        return (f"Runtime Error:\n{safe(run.stderr)}", safe(run.stderr))

                    return (safe(run.stdout), safe(run.stderr))
                except subprocess.TimeoutExpired:
                    return ("Time Limit Exceeded", "")
                except Exception as e:
                    return (f"Internal Error: {e}", "")

        # ---- Fallback via PISTON ----
        try:
            r = requests.post(
                PISTON,
                json={
                    "language": "cpp",
                    "version": "10.2.0",
                    "files": [{"name": "main.cpp", "content": code}],
                    "stdin": stdin
                },
                timeout=time_limit + 2
            )
            data = r.json()

            out = safe(data.get("run", {}).get("stdout", ""))
            err = safe(data.get("run", {}).get("stderr", ""))

            comp = data.get("compile", {})
            if comp and comp.get("stderr"):
                return (f"Compilation Error:\n{safe(comp.get('stderr'))}", "")

            if err.strip():
                return (f"Runtime Error:\n{err}", err)

            return (out, err)

        except requests.Timeout:
            return ("Time Limit Exceeded", "")
        except Exception as e:
            return (f"API Error: {e}", "")

    return ("Unsupported language", "")
