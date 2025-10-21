import subprocess, tempfile, os

def run_submission(language, source_code):
    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, {
            "cpp": "main.cpp",
            "python": "main.py",
            "pypy": "main.py",
            "java": "Main.java"
        }[language])

        with open(src_path, "w") as f:
            f.write(source_code)

        # Command theo ngôn ngữ
        if language == "cpp":
            exe = os.path.join(tmp, "main")
            compile_cmd = ["g++", src_path, "-O2", "-std=c++17", "-o", exe]
            run_cmd = [exe]
        elif language == "python":
            compile_cmd = None
            run_cmd = ["python3", src_path]
        elif language == "pypy":
            compile_cmd = None
            run_cmd = ["pypy3", src_path]
        elif language == "java":
            compile_cmd = ["javac", src_path]
            run_cmd = ["java", "-cp", tmp, "Main"]
        else:
            return "Unsupported language"

        try:
            if compile_cmd:
                subprocess.run(compile_cmd, check=True, capture_output=True, text=True, timeout=10)
            run = subprocess.run(run_cmd, capture_output=True, text=True, timeout=5)
            if run.returncode != 0:
                return f"❌ Runtime Error:\n{run.stderr}"
            return run.stdout or "(No output)"
        except subprocess.CalledProcessError as e:
            return f"❌ Compilation Error:\n{e.stderr}"
        except subprocess.TimeoutExpired:
            return "⏰ Time Limit Exceeded"
        except Exception as e:
            return f"⚠️ Error: {e}"
