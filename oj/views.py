# path: oj/views.py
import json
import os
from django.shortcuts import render
from django.http import JsonResponse
from django.utils.safestring import mark_safe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from judge.run_code import run_program  # ✅ chạy code

# ✅ Import toàn bộ stage roadmap
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
# 🏠 TRANG CHÍNH
# ==============================
def home(request):
    return render(request, "home.html", {"stages": STAGES})


# ==============================
# 📘 ROADMAP VIEW
# ==============================
def roadmap_stage(request, stage_id):
    stage = next((s for s in STAGES if s["id"] == stage_id), None)
    if not stage:
        return render(request, "oj/not_found.html", {"message": "Không tìm thấy giai đoạn này."})

    # ✅ Load file HTML content cho mỗi topic
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
        return render(request, "oj/not_found.html", {"message": "Không tìm thấy giai đoạn này."})

    topics = stage.get("topics", [])
    if topic_index < 1 or topic_index > len(topics):
        return render(request, "oj/not_found.html", {"message": "Không tìm thấy nội dung chi tiết."})

    topic = topics[topic_index - 1]
    return render(request, "topic_detail.html", {"stage": stage, "topic": topic})


# ==============================
# 💻 CHẠY CODE TRỰC TUYẾN — TRANG RIÊNG
# ==============================
def run_code_page(request):
    return render(request, "run_code.html")


def run_code_online(request):
    if request.method == "POST":
        language = request.POST.get("language", "")
        code = request.POST.get("code", "")
        input_data = request.POST.get("input", "")
        try:
            result, _ = run_program(language, code, input_data)
        except Exception as e:
            result = f"Lỗi khi chạy code: {str(e)}"
        return JsonResponse({"output": result})
    return JsonResponse({"error": "Invalid request"})


# ==============================
# 🚀 API CHẠY CODE CHO ROADMAP (Fix online editor)
# ==============================
@csrf_exempt
def run_code_for_roadmap(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    lang = request.POST.get("language", "").strip()
    code = request.POST.get("code", "").strip()
    input_data = request.POST.get("input", "")

    if not lang or not code:
        return JsonResponse({"error": "Missing language or code"}, status=400)

    try:
        output, err = run_program(lang, code, input_data)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({
        "output": (output or "").strip(),
        "error": (err or "").strip()
    })


# ==============================
# 🧾 API chạy code cho Ajax JSON
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

    output, err = run_program(lang, code, input_data)
    return JsonResponse({"output": output, "error": err or ""})
