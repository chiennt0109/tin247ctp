import subprocess, tempfile, os, time

# Chỉ cho phép Python trong chế độ an toàn
def run_program(lang, code, stdin, time_limit=3):
    if lang not in ["python", "pypy"]:
        return ("Language disabled", "")

    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "main.py")
        with open(src, "w") as f:
            f.write(code)

        try:
            result = subprocess.run(
                ["python3", src] if lang == "python" else ["pypy3", src],
                input=stdin,
                text=True,
                capture_output=True,
                timeout=time_limit
            )

            if result.returncode != 0:
                return ("Runtime Error:\n" + result.stderr, "")

            return (result.stdout, "")

        except subprocess.TimeoutExpired:
            return ("Time Limit Exceeded", "")
        except Exception as e:
            return ("Internal Error: " + str(e), "")
