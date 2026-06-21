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
from .roadmap_data import STAGES

import html
from learning_analytics.leaderboard_service import LearningLeaderboardService



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

ROADMAP_TRACKS = [
    {"name": "Nền tảng C++ và phân tích độ phức tạp", "stage_ids": [1, 3], "goal": "Nắm cú pháp C++ cốt lõi, tư duy thuật toán nhập môn và Big-O theo hướng CLRS/DSA Analysis.", "prerequisites": "Chưa yêu cầu; biết sử dụng máy tính và tư duy logic cơ bản.", "level": "Nhập môn"},
    {"name": "Cấu trúc dữ liệu cơ bản", "stage_ids": [2, 8], "goal": "Làm chủ mảng, chuỗi, hàm, file và ADT tuyến tính như stack, queue, linked list, hash table.", "prerequisites": "Biến, rẽ nhánh, vòng lặp và thao tác nhập xuất.", "level": "Cơ bản"},
    {"name": "Sắp xếp, tìm kiếm", "stage_ids": [5], "goal": "Hiểu tìm kiếm, sắp xếp, đệ quy và chia để trị; kết nối với phân tích độ phức tạp.", "prerequisites": "Mảng, hàm, độ phức tạp cơ bản.", "level": "Cơ bản → Trung cấp"},
    {"name": "Kỹ thuật giải bài", "stage_ids": [4, 7], "goal": "Rèn mô hình hóa bài toán, mô phỏng, quay lui và nhánh cận theo phong cách Competitive Programming.", "prerequisites": "Cấu trúc dữ liệu cơ bản và khả năng cài đặt thuật toán ngắn.", "level": "Trung cấp"},
    {"name": "Quy hoạch động", "stage_ids": [6], "goal": "Nhận diện trạng thái, công thức chuyển và tối ưu bộ nhớ cho các mẫu DP kinh điển.", "prerequisites": "Đệ quy, mảng, tư duy chia nhỏ bài toán.", "level": "Trung cấp"},
    {"name": "Cây", "stage_ids": [11], "goal": "Nắm cây tìm kiếm, cây cân bằng và các cấu trúc cây phục vụ truy vấn/phân hoạch dữ liệu.", "prerequisites": "Đệ quy, con trỏ/ADT, stack/queue.", "level": "Trung cấp → Nâng cao"},
    {"name": "Đồ thị", "stage_ids": [9, 10], "goal": "Biểu diễn đồ thị, duyệt, đường đi ngắn nhất và cây khung nhỏ nhất.", "prerequisites": "Queue, stack, priority queue và phân tích độ phức tạp.", "level": "Trung cấp → Nâng cao"},
    {"name": "Cấu trúc dữ liệu nâng cao", "stage_ids": [12, 13], "goal": "Bổ sung toán rời rạc, lý thuyết số và thuật toán chuỗi cho bài toán nâng cao.", "prerequisites": "Mảng, hash, cây và kỹ thuật tối ưu cơ bản.", "level": "Nâng cao"},
    {"name": "Luyện thi", "stage_ids": [14], "goal": "Ghép kỹ thuật DP, Graph, Math; luyện debug, code sạch và chiến thuật làm bài.", "prerequisites": "Hoàn thành các chặng nền tảng, dữ liệu, cây/đồ thị và DP.", "level": "Thi đấu"},
]

def build_roadmap_tracks(stages):
    stage_by_id = {stage["id"]: stage for stage in stages}
    tracks = []
    completed_before = 0
    total_lessons = sum(len(stage.get("topics", [])) for stage in stages) or 1
    for index, track in enumerate(ROADMAP_TRACKS, start=1):
        chapters = []
        lesson_count = 0
        for stage_id in track["stage_ids"]:
            stage = stage_by_id.get(stage_id)
            if not stage:
                continue
            topics = []
            for topic_index, topic in enumerate(stage.get("topics", []), start=1):
                title = topic.get("title", "")
                topic_type = "Bài tập" if any(k in title.lower() for k in ["solver", "bài", "n-queens", "sudoku"]) else ("Ví dụ" if topic.get("sample_cpp") or topic.get("sample_py") else "Lý thuyết")
                topics.append({"lesson": topic, "index": topic_index, "type": topic_type, "level": track["level"]})
            lesson_count += len(topics)
            chapters.append({"stage": stage, "topics": topics})
        tracks.append({**track, "index": index, "chapters": chapters, "lesson_count": lesson_count, "progress": round((completed_before / total_lessons) * 100)})
        completed_before += lesson_count
    return tracks

# ==============================
# 🏠 HOME
# ==============================
def home(request):
    leaderboard = LearningLeaderboardService().compute(top_n=10)
    return render(request, "home.html", {"stages": STAGES, "roadmap_tracks": build_roadmap_tracks(STAGES), "learning_leaderboard": leaderboard})


# ==============================
# 📚 ROADMAP STAGE + TOPIC
# ==============================
def roadmap_stage(request, stage_id):
    stage = next((s for s in STAGES if s["id"] == stage_id), None)
    if not stage:
        return render(request, "oj/not_found.html", {"message": "Không tìm thấy giai đoạn."})

    # ✅ chuyển Python list → JSON string
    stage_json = json.dumps(stage["topics"], ensure_ascii=False)

    # Lấy prev/next stage (tuỳ bạn có hay không)
    prev_stage = next((s for s in STAGES if s["id"] == stage_id - 1), None)
    next_stage = next((s for s in STAGES if s["id"] == stage_id + 1), None)

    return render(request, "roadmap_stage.html", {
        "stage": stage,
        "stage_json": stage_json,  # thêm biến này
        "prev_stage": prev_stage,
        "next_stage": next_stage,
    })


def topic_detail(request, stage_id, topic_index):
    # 🔍 Lấy stage tương ứng
    stage = next((s for s in STAGES if s["id"] == stage_id), None)
    if not stage:
        return render(request, "oj/not_found.html", {"message": "Không tìm thấy nội dung."})

    topics = stage.get("topics", [])
    if topic_index < 1 or topic_index > len(topics):
        return render(request, "oj/not_found.html", {"message": "Không tìm thấy nội dung chi tiết."})

    topic = topics[topic_index - 1]

    # ✅ Làm sạch & giải mã detail nếu có sẵn trong dict
    if "detail" in topic and isinstance(topic["detail"], str):
        topic["detail"] = html.unescape(topic["detail"]).replace("\\n", "<br>")

    # ✅ Nếu chưa có detail, thử đọc từ file html_file
    if not topic.get("detail") and topic.get("html_file"):
        # Tạo đường dẫn tuyệt đối từ BASE_DIR
        html_path = os.path.join(settings.BASE_DIR, "oj", topic["html_file"])
        try:
            # Đảm bảo thư mục tồn tại
            if not os.path.exists(html_path):
                topic["detail"] = (
                    f"<p class='text-danger'>⚠️ Không tìm thấy file nội dung: "
                    f"<code>{topic['html_file']}</code></p>"
                )
            else:
                try:
                    # Đọc file theo UTF-8, bỏ qua ký tự lỗi nếu có
                    with open(html_path, "r", encoding="utf-8", errors="replace") as f:
                        topic["detail"] = f.read()
                except UnicodeDecodeError as e:
                    # Nếu vẫn lỗi mã hóa, hiển thị thông báo cụ thể
                    topic["detail"] = (
                        f"<p class='text-danger'>⚠️ File tồn tại nhưng lỗi mã hóa: {html_path}</p>"
                        f"<pre>{html.escape(str(e))}</pre>"
                    )
        except Exception as e:
            topic["detail"] = (
                "<p class='text-danger'>⚠️ Lỗi khi đọc nội dung chi tiết.</p>"
                f"<pre>{html.escape(str(e))}</pre>"
            )

    # ✅ Trả về trang chi tiết
    return render(request, "roadmap_detail.html", {
        "stage": stage,
        "topic": topic,
    })



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
