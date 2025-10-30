# path: judge/run_code.py
import subprocess, tempfile, os, sys

def run_program(lang, code, stdin, time_limit=3):
    with tempfile.TemporaryDirectory() as tmpdir:
        if lang == "python" or lang == "pypy":
            src = os.path.join(tmpdir, "main.py")
            with open(src, "w") as f:
                f.write(code)
            try:
                r = subprocess.run(
                    ["python3", src],
                    input=stdin,
                    text=True,
                    capture_output=True,
                    timeout=time_limit
                )
            except subprocess.TimeoutExpired:
                return ("Time Limit Exceeded", "")
            
            if r.returncode != 0:
                return ("Runtime Error:\n" + r.stderr, "")
            return (r.stdout, "")

        elif lang == "cpp":
            # Render không có g++ → chỉ chấm local được
            gpp = "/usr/bin/g++"
            if not os.path.exists(gpp):
                return ("C++ not supported on this server", "")
            
            src = os.path.join(tmpdir, "main.cpp")
            binfile = os.path.join(tmpdir, "a.out")
            with open(src, "w") as f:
                f.write(code)

            c = subprocess.run([gpp, src, "-O2", "-std=gnu++17", "-o", binfile], capture_output=True, text=True)
            if c.returncode != 0:
                return ("Compilation Error:\n" + c.stderr, "")

            try:
                r = subprocess.run(
                    [binfile],
                    input=stdin,
                    text=True,
                    capture_output=True,
                    timeout=time_limit
                )
            except subprocess.TimeoutExpired:
                return ("Time Limit Exceeded", "")

            if r.returncode != 0:
                return ("Runtime Error:\n" + r.stderr, "")
            return (r.stdout, "")

        else:
            return ("Unsupported language", "")
