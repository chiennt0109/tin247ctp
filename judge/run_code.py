import subprocess, tempfile, os, sys, signal

def run_program(mode, code_or_bin, input_data, time_limit=2):
    tmp = tempfile.mkdtemp()
    
    # =======================
    # 1️⃣ Compile C++
    # =======================
    if mode == "compile_cpp":
        source = os.path.join(tmp, "code.cpp")
        exe = os.path.join(tmp, "a.out")

        with open(source, "w") as f:
            f.write(code_or_bin)

        cmd = ["g++", "-std=c++17", "-O2", source, "-o", exe]

        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if p.returncode != 0:
            return ("Compilation Error", p.stderr)

        # ✅ return path to binary in stderr field (grader expects this)
        return ("OK", exe)

    # =======================
    # 2️⃣ Run compiled C++ bin
    # =======================
    if mode == "run_cpp_bin":
        try:
            p = subprocess.run(
                [code_or_bin],
                input=input_data,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=time_limit
            )
            if p.returncode != 0:
                return ("Runtime Error", p.stderr)

            return (p.stdout, p.stderr)

        except subprocess.TimeoutExpired:
            return ("Time Limit Exceeded", "")

        except Exception as e:
            return ("Runtime Error", str(e))

    # =======================
    # 3️⃣ Run Python
    # =======================
    if mode == "python":
        source = os.path.join(tmp, "code.py")
        with open(source, "w") as f:
            f.write(code_or_bin)

        try:
            p = subprocess.run(
                ["python3", source],
                input=input_data,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=time_limit
            )
            if p.returncode != 0:
                return ("Runtime Error", p.stderr)

            return (p.stdout, p.stderr)

        except subprocess.TimeoutExpired:
            return ("Time Limit Exceeded", "")

        except Exception as e:
            return ("Runtime Error", str(e))

    return ("Internal Error", "Invalid mode")
