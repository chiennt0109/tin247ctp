import time
from problems.models import TestCase
from .run_code import run_program

def _normalize(s: str) -> str:
    if s is None:
        return ""
    return s.replace("\r\n", "\n").rstrip()

def _compare_output(user_out: str, expected_out: str) -> bool:
    u = [line.rstrip() for line in _normalize(user_out).split("\n")]
    e = [line.rstrip() for line in _normalize(expected_out).split("\n")]
    # bỏ dòng trống cuối
    while u and u[-1] == "": u.pop()
    while e and e[-1] == "": e.pop()
    if len(u) != len(e): 
        return False
    for a, b in zip(u, e):
        if a != b: 
            return False
    return True

def grade_submission(submission):
    """
    Trả về: (verdict, total_time, passed, total, logs)
    logs = list[dict] chứa thông tin từng test để debug.
    """
    problem = submission.problem
    tests = TestCase.objects.filter(problem=problem).order_by("id")

    total = tests.count()
    passed = 0
    total_time = 0.0
    logs = []

    for idx, tc in enumerate(tests, 1):
        start = time.time()
        out, err = run_program(
            submission.language,
            submission.source_code,
            tc.input_data,
            time_limit=max(int(problem.time_limit), 1)
        )
        elapsed = max(0.0, time.time() - start)
        total_time += elapsed

        status = "OK"
        verdict_here = None

        # Phân loại lỗi sớm
        if isinstance(out, str) and out.startswith("Compilation Error"):
            status = "Compilation Error"
            verdict_here = "Compilation Error"
        elif isinstance(out, str) and out.startswith("Runtime Error"):
            status = "Runtime Error"
            verdict_here = "Runtime Error"
        elif out == "Time Limit Exceeded":
            status = "Time Limit Exceeded"
            verdict_here = "Time Limit Exceeded"
        elif isinstance(out, str) and out.startswith("API Error"):
            status = "Runtime Error"
            verdict_here = "Runtime Error"
        else:
            # So sánh output
            if _compare_output(out, tc.expected_output):
                passed += 1
                status = "AC"
            else:
                status = "WA"
                verdict_here = "Wrong Answer"

        logs.append({
            "no": idx,
            "test_id": tc.id,
            "elapsed": elapsed,
            "status": status,
            "input": tc.input_data,
            "expected": tc.expected_output,
            "output": _normalize(out),
            "stderr": (err or "")
        })

        # Nếu test này fail → dừng sớm nhưng vẫn trả lại toàn bộ log đã ghi
        if verdict_here:
            return (verdict_here, total_time, passed, total, logs)

    # qua hết
    return ("Accepted", total_time, passed, total, logs)
