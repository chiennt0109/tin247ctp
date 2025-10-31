import subprocess, tempfile, os, json, sys, signal

def run_program(lang, code, input_data, time_limit=2):
    tmp = tempfile.mkdtemp()
    source = os.path.join(tmp, "code")

    if lang == "cpp":
        source += ".cpp"
        exe = os.path.join(tmp, "run")

        with open(source, "w") as f:
            f.write(code)

        # Compile C++
        compile_cmd = ["g++", "-std=c++17", source, "-O2", "-o", exe]
        comp = subprocess.run(
            compile_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        if comp.returncode != 0:
            return "Compilation Error", comp.stderr

        run_cmd = [exe]

    elif lang == "python":
        source += ".py"
        with open(source, "w") as f:
            f.write(code)
        run_cmd = ["python3", source]

    else:
        return "Internal Error", "Unsupported language"

    try:
        p = subprocess.run(
            run_cmd,
            input=input_data,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=time_limit
        )
        return p.stdout, p.stderr

    except subprocess.TimeoutExpired:
        return "Time Limit Exceeded", ""

    except Exception as e:
        return "Runtime Error", str(e)
