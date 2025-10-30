# path: judge/run_code.py
import os, requests, time

JUDGE0_URL = "https://judge0-ce.p.rapidapi.com/submissions"
JUDGE0_HEADERS = {
    "X-RapidAPI-Key": os.getenv("JUDGE0_API_KEY", ""),
    "X-RapidAPI-Host": "judge0-ce.p.rapidapi.com",
    "Content-Type": "application/json"
}

LANG_MAP = {
    "cpp": 54,     # GCC 17
    "python": 71,  # Python 3.11
    "pypy": 70,    # PyPy
    "java": 62     # Java 17
}

def run_program(lang, code, stdin, time_limit=2):
    if lang not in LANG_MAP:
        return ("", "Unsupported language")

    payload = {
        "language_id": LANG_MAP[lang],
        "source_code": code,
        "stdin": stdin,
        "cpu_time_limit": time_limit,
        "wall_time_limit": time_limit + 1,
        "memory_limit": 256000,
        "enable_per_process_and_thread_time_limit": True
    }

    try:
        r = requests.post(JUDGE0_URL + "?base64_encoded=false&wait=false",
                          json=payload, headers=JUDGE0_HEADERS, timeout=10)
        token = r.json().get("token", None)
        if not token:
            return ("", "Judge0 did not return token")

        # Polling
        for _ in range(60):
            time.sleep(0.15)
            res = requests.get(f"{JUDGE0_URL}/{token}?base64_encoded=false",
                               headers=JUDGE0_HEADERS).json()

            status = res.get("status", {}).get("description", "")

            if status in ["In Queue", "Processing"]:
                continue

            stdout = res.get("stdout", "") or ""
            stderr = res.get("stderr", "") or ""
            compile_err = res.get("compile_output", "") or ""

            # unify error output
            if compile_err:
                return ("", "Compilation Error:\n" + compile_err)
            if stderr:
                return ("", "Runtime Error:\n" + stderr)
            if status == "Time Limit Exceeded":
                return ("", "Time Limit Exceeded")

            return (stdout, "")

        return ("", "Time Limit Exceeded")

    except Exception as e:
        return ("", f"System Error: {e}")
