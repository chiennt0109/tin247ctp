# path: judge/run_code.py
import os, requests, time, tempfile, subprocess

JUDGE0_URL = "https://judge0-ce.p.rapidapi.com/submissions"
JUDGE0_HEADERS = {
    "X-RapidAPI-Key": os.getenv("JUDGE0_API_KEY", ""),
    "X-RapidAPI-Host": "judge0-ce.p.rapidapi.com",
    "Content-Type": "application/json"
}

LANG_MAP = {
    "cpp": 54,     # GCC 17
    "python": 71,  # Python 3.11
    "pypy": 70,    # PyPy 7.3
    "java": 62     # Java 17
}

def run_program(lang, code, stdin, time_limit=3):
    if lang not in LANG_MAP:
        return ("Unsupported language", "")

    payload = {
        "language_id": LANG_MAP[lang],
        "source_code": code,
        "stdin": stdin,
        "cpu_time_limit": time_limit,
        "wall_time_limit": time_limit + 1,
        "memory_limit": 256000,
        "enable_per_process_and_thread_time_limit": True,
        "compiler_options": "",
        "command_line_arguments": ""
    }

    r = requests.post(JUDGE0_URL + "?base64_encoded=false&wait=false",
                      json=payload, headers=JUDGE0_HEADERS)
    token = r.json().get("token")

    # ✅ Poll kết quả
    for _ in range(50):
        time.sleep(0.15)
        res = requests.get(f"{JUDGE0_URL}/{token}?base64_encoded=false",
                           headers=JUDGE0_HEADERS).json()

        status = res.get("status", {}).get("description", "")
        stdout = res.get("stdout", "")
        stderr = res.get("stderr", "")
        compile_err = res.get("compile_output", "")

        if status in ["Queue", "Processing"]:
            continue

        if compile_err:
            return ("Compilation Error:\n" + compile_err, "")
        if stderr:
            return ("Runtime Error:\n" + stderr, "")
        return (stdout or "", "")

    return ("Time Limit Exceeded", "")
