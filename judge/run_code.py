import requests, tempfile, os, subprocess, json

JUDGE0_URL = "https://judge0-ce.p.rapidapi.com/submissions"
JUDGE0_HEADERS = {
    "x-rapidapi-host": "judge0-ce.p.rapidapi.com",
    "x-rapidapi-key": "YOUR_RAPIDAPI_KEY",   # ❗ Thay key của bạn vào đây
    "content-type": "application/json"
}

LANG_MAP = {
    "cpp": 54,      # g++ 17
    "python": 71,   # Python 3.11
    "pypy": 99,     # PyPy 3
    "java": 62      # Java 17
}

# ✅ Cache compile C++ để tăng tốc
COMPILE_CACHE = {}

def run_judge0(language, code, input_data):
    # ✅ check cache (chỉ áp dụng với C++)
    cache_key = code.strip()
    if language == "cpp" and cache_key in COMPILE_CACHE:
        token = COMPILE_CACHE[cache_key]
    else:
        payload = {
            "source_code": code,
            "language_id": LANG_MAP.get(language),
            "stdin": input_data,
            "compiler_options": "-O2 -std=gnu++17",
        }

        r = requests.post(JUDGE0_URL, data=json.dumps(payload), headers=JUDGE0_HEADERS)
        if r.status_code != 201:
            return f"API Error {r.status_code}", ""

        token = r.json()["token"]

        # ✅ Lưu token compile vào cache
        if language == "cpp":
            COMPILE_CACHE[cache_key] = token

    # ✅ GET kết quả
    while True:
        r = requests.get(f"{JUDGE0_URL}/{token}", headers=JUDGE0_HEADERS)
        data = r.json()
        status = data["status"]["description"]

        if status in ["In Queue", "Processing"]:
            continue

        stdout = data.get("stdout", "") or ""
        stderr = data.get("stderr", "") or ""
        compile_output = data.get("compile_output", "")

        if compile_output:
            return f"Compilation Error:\n{compile_output}", ""

        if stderr:
            return f"Runtime Error:\n{stderr}", ""

        return stdout, ""

def run_program(language: str, code: str, input_data: str, time_limit=5):
    # ✅ Python local cho roadmap
    if language in ["python", "pypy"]:
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "main.py")
            open(src, "w").write(code)
            try:
                p = subprocess.run(["python3", src], input=input_data,
                                   capture_output=True, text=True, timeout=time_limit)
                if p.returncode != 0:
                    return f"Runtime Error:\n{p.stderr}", ""
                return p.stdout, ""
            except subprocess.TimeoutExpired:
                return "Time Limit Exceeded", ""

    # ✅ C++, Java → Judge0
    if language in ["cpp", "java"]:
        return run_judge0(language, code, input_data)

    return f"Unsupported language: {language}", ""
