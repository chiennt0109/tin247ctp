# path: oj/views.py
from django.shortcuts import render
from django.http import JsonResponse, Http404
from judge.run_code import run_program
from .roadmap_data import STAGES  # ✅ import toàn bộ dữ liệu

def home(request):
    """Trang chủ hiển thị danh sách các giai đoạn"""
    stages = [
        (s["title"], s["summary"], [t["title"] for t in s["topics"]], f"stage-{s['id']}", "sky")
        for s in STAGES
    ]
    return render(request, "home.html", {"stages": stages})


def roadmap_stage(request, stage_id):
    """Hiển thị danh sách chủ đề của một giai đoạn"""
    stage = next((s for s in STAGES if s["id"] == stage_id), None)
    if not stage:
        raise Http404("Không tìm thấy giai đoạn.")
    idx = STAGES.index(stage)
    prev_stage = STAGES[idx - 1] if idx > 0 else None
    next_stage = STAGES[idx + 1] if idx < len(STAGES) - 1 else None
    return render(request, "roadmap_stage.html", {
        "stage": stage,
        "prev_stage": prev_stage,
        "next_stage": next_stage
    })


def run_code_online(request):
    """Xử lý chạy code trực tuyến"""
    if request.method == "POST":
        lang = request.POST.get("language", "")
        code = request.POST.get("code", "")
        input_data = request.POST.get("input", "")
        try:
            output = run_program(lang, code, input_data)
            if isinstance(output, (list, tuple)):
                output = output[0]
        except Exception as e:
            output = f"Lỗi khi chạy code: {str(e)}"
        return JsonResponse({"output": str(output).strip()})
    return JsonResponse({"error": "Invalid request"})


def topic_detail(request, stage_id, topic_index):
    """Trang chi tiết từng chủ đề"""
    stage = next((s for s in STAGES if s["id"] == stage_id), None)
    if not stage:
        raise Http404("Không tìm thấy giai đoạn.")
    try:
        t_idx = int(topic_index) - 1
        topic = stage["topics"][t_idx]
    except Exception:
        raise Http404("Không tìm thấy chủ đề.")
    return render(request, "topic_detail.html", {"stage": stage, "topic": topic})
