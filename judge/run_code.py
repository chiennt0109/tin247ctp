import os
import time
import requests

# Judge0 CE (RapidAPI – extra/compile cache)
JUDGE0_HOST = "judge0-ce.p.rapidapi.com"
JUDGE0_URL = f"https://{JUDGE0_HOST}/submissions"
JUDGE0_KEY = os.getenv("JUDGE0_API_KEY", "").strip()

HEADERS = {
    "X-RapidAPI-Key": JUDGE0_KEY,
    "X-RapidAPI-Host": JUDGE0_HOST,
    "Content-Type": "application/json",
}

# Mapping language_id theo Judge0 CE
LANG_MAP = {
    "cpp": 54,     # C++ (GCC)
    "python": 71,  # Python 3.11
    "pypy": 70,    # PyPy
    "java": 62,    # Java 17
}

def _api_error(msg):
    return (f"API Error: {msg}", "")

def run_program(lang: str, code: str, stdin: str, time_limit: int = 3):
    """
    Gửi code tới Judge0 và poll kết quả.
    - Trả về (stdout, stderrInfoAsStringForDbg) hoặc chuỗi báo lỗi đặc biệt:
      "Compilation Error: ...", "Runtime Error: ...", "Time Limit Exceeded", "API Error: ..."
    """
    if lang not in LANG_MAP:
        return (f"API Error: Unsupported language {lang}", "")

    if not JUDGE0_KEY:
        return (f"API Error: Missing JUDGE0_API_KEY", "")

    payload = {
        "language_id": LANG_MAP[lang],
        "source_code": code or "",
        "stdin": stdin or "",
        # Các trường limit nâng cao có thể bị ignore trên CE,
        # nhưng để lại giá trị để tương thích với extra:
        "cpu_time_limit": max(1, int(time_limit)),
        "wall_time_limit": max(1, int(time_limit)) + 1,
        "enable_per_process_and_thread_time_limit": True,
    }

    try:
        # Tạo submission (không wait)
        create = requests.post(
            JUDGE0_URL + "?base64_encoded=false&wait=false",
            headers=HEADERS, json=payload, timeout=max(5, time_limit + 3)
        )
        if create.status_code != 201:
            return _api_error(f"create {create.status_code}: {create.text}")

        token = (create.json() or {}).get("token")
        if not token:
            return _api_error("no token returned")

        # Poll kết quả
        deadline = time.time() + max(3, time_limit + 5)
        while time.time() < deadline:
            time.sleep(0.2)
            res = requests.get(
                f"{JUDGE0_URL}/{token}?base64_encoded=false&fields=stdout,stderr,compile_output,status,status_id,message",
                headers=HEADERS, timeout=5
            )
            if res.status_code != 200:
                # tiếp tục poll nhẹ nếu tạm thời
                continue

            data = res.json() or {}
            status = (data.get("status") or {}).get("description", "")
            status_id = (data.get("status") or {}).get("id", 0)
            stdout = data.get("stdout") or ""
            stderr = data.get("stderr") or ""
            compile_output = data.get("compile_output") or ""
            message = data.get("message") or ""

            # Các trạng thái đang chạy
            if status_id in (1, 2):  # In Queue, Processing
                continue

            # Hoàn thành hoặc lỗi:
            if compile_output:
                return ("Compilation Error:\n" + compile_output, "")
            if status_id == 5:  # Time Limit Exceeded
                return ("Time Limit Exceeded", "")
            if status_id in (6, 7):  # Compilation error (6) đã bắt ở compile_output, 7: Runtime Error (CE variants)
                return ("Runtime Error:\n" + (stderr or message), "")
            if status_id in (11, 12):  # Exec Format / Internal Error
                return ("Runtime Error:\n" + (stderr or message or status), "")

            # Accepted hoặc những status khác có stdout
            # (AC = 3 theo Judge0)
            return (stdout, "")

        return ("Time Limit Exceeded", "")

    except requests.Timeout:
        return ("Time Limit Exceeded", "")
    except Exception as e:
        return _api_error(str(e))
