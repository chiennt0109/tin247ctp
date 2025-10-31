import subprocess, tempfile, os, shutil

def _clean(s, n=2000):
    return (s or "")[:n]

def run_program(lang, code, input_data, time_limit=3):
    lang = lang.lower()

    # -------- Python ----------
    if lang in ("python", "pypy"):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "main.py")
            with open(src, "w") as f: f.write(code)

            cmd = ["python3", src] if lang == "python" else ["pypy3", src]

            try:
                p = subprocess.run(cmd, input=input_data, text=True,
                                   capture_output=True, timeout=time_limit)
            except subprocess.TimeoutExpired:
                return ("Time Limit Exceeded", "")

            if p.returncode != 0:
                return ("Runtime Error:\n" + _clean(p.stderr), p.stderr)
            return (p.stdout, p.stderr)

    # -------- C++ ----------
    if lang == "cpp":
        tmp = tempfile.mkdtemp()
        src = os.path.join(tmp, "main.cpp")
        bin = os.path.join(tmp, "a.out")

        with open(src, "w") as f: f.write(code)

        # compile
        cp = subprocess.run(
            ["g++", src, "-O2", "-std=gnu++17", "-o", bin],
            capture_output=True, text=True
        )
        if cp.returncode != 0:
            shutil.rmtree(tmp)
            return ("Compilation Error:\n" + _clean(cp.stderr), cp.stderr)

        # run
        try:
            p = subprocess.run([bin], input=input_data, text=True,
                               capture_output=True, timeout=time_limit)
        except subprocess.TimeoutExpired:
            shutil.rmtree(tmp)
            return ("Time Limit Exceeded", "")

        out, err = p.stdout, p.stderr
        shutil.rmtree(tmp)

        if p.returncode != 0:
            return ("Runtime Error:\n" + _clean(err), err)

        return (out, err)

    return (f"Unsupported language: {lang}", "")
