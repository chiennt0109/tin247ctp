# path: oj/views.py
import json
import os
import time
import requests

from django.shortcuts import render
from django.http import JsonResponse
from django.utils.safestring import mark_safe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from judge.run_code import run_program  # dùng cho demo run & backup

# ==============================
# ✅ Import Roadmap Stages
# ==============================
from .roadmap_data.stage_01 import STAGE_1
from .roadmap_data.stage_02 import STAGE_2
from .roadmap_data.stage_03 import STAGE_3
from .roadmap_data.stage_04 import STAGE_4
from .roadmap_data.stage_05 import STAGE_5
from .roadmap_data.stage_06 import STAGE_6
from .roadmap_data.stage_07 import STAGE_7
from .roadmap_data.stage_08 import STAGE_8
from .roadmap_data.stage_09 import STAGE_9
from .roadmap_data.stage_10 import STAGE_10
from .roadmap_data.stage_11 import STAGE_11
from .roadmap_data.stage_12 import STAGE_12
from .roadmap_data.stage_13 import STAGE_13
from .roadmap_data.stage_14 import STAGE_14

STAGES = [
    STAGE_1, STAGE_2, STAGE_3, STAGE_4, STAGE_5, STAGE_6, STAGE_7,
    STAGE_8, STAGE_9, STAGE_10, STAGE_11, STAGE_12, STAGE_13, STAGE_14
]

# ==============================
# 🏠 HOME
# ==============================
def home(request):
    return render(request, "home.html", {"stages": STAGES})


# ==============================
# 📚 ROADMAP STAGE + TOPIC
# ==============================
def roadmap_stage(request, stage_id):
    stage = next((s for s in STAGES if s["id"] == stage_id), None)
    if not stage:
        return render(request, "oj/not_found.html", {"message": "Không tìm thấy giai đoạn này."})

    for topic in stage.get("topics", []):
        html_file = topic.get("html_file")
        if html_file:
            full_path = os.path.join(settings.BASE_DIR, "oj", html_file)
            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    topic["detail"] = mark_safe(f.read())

    idx = STAGES.index(stage)
    prev_stage = STAGES[idx - 1] if idx > 0 else None
    next_stage = STAGES[idx + 1] if idx < len(STAGES) - 1 else None

    return render(request, "roadmap_stage.html", {
        "stage": stage,
        "prev_stage": prev_stage,
        "next_stage": next_stage
    })


def topic_detail(request, stage_id, topic_index):
    stage = next((s for s in STAGES if s["id"] == stage_id), None)
    if not stage:
        return render(request, "oj/not_found.html", {"message": "Không tìm thấy nội dung."})

    topics = stage.get("topics", [])
    if topic_index < 1 or topic_index > len(topics):
        return render(request, "oj/not_found.html", {"message": "Không tìm thấy nội dung chi tiết."})

    topic = topics[topic_index - 1]
    return render(request, "topic_detail.html", {"stage": stage, "topic": topic})


# ==============================
# 💻 RUN CODE — TRANG DEMO
# ==============================
def run_code_page(request):
    return render(request, "run_code.html")


def run_code_online(request):
    if request.method == "POST":
        lang = request.POST.get("language")
        code = request.POST.get("code")
        input_data = request.POST.get("input", "")
        try:
            result, _ = run_program(lang, code, input_data)
        except Exception as e:
            result = f"Lỗi khi chạy code: {str(e)}"
        return JsonResponse({"output": result})
    return JsonResponse({"error": "Invalid request"})


# ==============================
# 🚀 RUN CODE FOR ROADMAP (Judge0)
# ==============================
@csrf_exempt
def run_code_for_roadmap(request):
    """
    This runner = for learning only (small input)
    Python runs locally, C++ uses fallback API ONLY here.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    lang = request.POST.get("language", "").strip()
    code = request.POST.get("code", "").strip()
    input_data = request.POST.get("input", "")

    if not lang or not code:
        return JsonResponse({"error": "Missing language or code"}, status=400)

    # ✅ Run Python locally
    if lang == "python":
        import subprocess, tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(code.encode())
            filename = f.name
        try:
            r = subprocess.run(
                ["python3", filename],
                input=input_data,
                capture_output=True,
                text=True,
                timeout=3
            )
            return JsonResponse({"output": r.stdout, "error": r.stderr})
        except Exception as e:
            return JsonResponse({"output": "", "error": str(e)})
        finally:
            os.remove(filename)

    # ✅ C++ fallback ONLY for roadmap (not judge)
    if lang == "cpp":
        try:
            payload = {
                "source": code,
                "input": input_data
            }
            r = requests.post(
                "https://wandbox.org/api/compile.json",
                json={
                    "code": code,
                    "stdin": input_data,
                    "compiler": "gcc-13.2.0",
                    "options": "warning,gnu++17,timeout=2",
                },
                timeout=5
            ).json()

            return JsonResponse({
                "output": r.get("program_output", "") or "",
                "error": r.get("compiler_error", "") + r.get("program_error", "")
            })
        except Exception as e:
            return JsonResponse({"output": "", "error": str(e)})

    return JsonResponse({"error": "Language not supported"}, status=400)


# ==============================
# 🧾 API run for AJAX (giữ nguyên bản cũ)
# ==============================
@csrf_exempt
def api_run_code(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    try:
        data = json.loads(request.body)
    except:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    lang = data.get("language", "").strip()
    code = data.get("code", "").strip()
    input_data = data.get("input", "")

    if not lang or not code:
        return JsonResponse({"error": "Missing language or code"}, status=400)

    out, err = run_program(lang, code, input_data)
    return JsonResponse({"output": out, "error": err or ""})
