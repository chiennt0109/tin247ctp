import subprocess, tempfile, os, shutil

def run_program(language, code_or_bin, input_data, time_limit=2):
    language = language.lower()

    # Python
    if language == "python":
        with tempfile.TemporaryDirectory() as tmp:
            src = tmp + "/main.py"
            open(src, "w").write(code_or_bin)
            try:
                p = subprocess.run(["python3", src], input=input_data, text=True,
                                   capture_output=True, timeout=time_limit)
                if p.returncode != 0:
                    return ("Runtime Error", p.stderr)
                return (p.stdout, "")
            except subprocess.TimeoutExpired:
                return ("Time Limit Exceeded", "")

    # C++ compile
    if language == "compile_cpp":
        with tempfile.TemporaryDirectory() as tmp:
            cpp = tmp + "/main.cpp"
            out = tmp + "/a.out"
            open(cpp, "w").write(code_or_bin)
            p = subprocess.run(["g++", cpp, "-O2", "-std=c++17", "-o", out],
                               capture_output=True, text=True)
            if p.returncode != 0:
                return ("Compilation Error", p.stderr)
            return ("OK", out)

    # C++ run compiled binary
    if language == "run_cpp_bin":
        try:
            p = subprocess.run([code_or_bin], input=input_data, text=True,
                               capture_output=True, timeout=time_limit)
            if p.returncode != 0:
                return ("Runtime Error", p.stderr)
            return (p.stdout, "")
        except subprocess.TimeoutExpired:
            return ("Time Limit Exceeded", "")

    return ("Unknown Language", "")
