# path: oj/views.py
import json
import os
import time
import re
import unicodedata
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

ROADMAP_CHAPTERS = [
    {"title": "Nền tảng C++", "stage_ids": [1], "extras": ["STL cơ bản: vector, pair, tuple", "Iterator, range-based for"]},
    {"title": "Kiểu dữ liệu trừu tượng và thư viện chuẩn", "stage_ids": [2, 8], "extras": ["STL algorithm: sort, lower_bound, upper_bound", "set, multiset, map, unordered_map"]},
    {"title": "Phân tích thuật toán, tìm kiếm và sắp xếp", "stage_ids": [3, 5], "extras": ["Amortized analysis", "Counting sort, radix sort, heap sort"]},
    {"title": "Kỹ thuật giải bài cơ bản", "stage_ids": [4], "extras": ["Prefix sum", "Difference array", "Two pointers", "Sliding window"]},
    {"title": "Đệ quy, quay lui và nhánh cận", "stage_ids": [7], "extras": ["Bitmask enumeration", "Meet-in-the-middle"]},
    {"title": "Quy hoạch động", "stage_ids": [6], "extras": ["DP trên bitmask", "DP trên cây", "DP tối ưu không gian"]},
    {"title": "Cây và truy vấn đoạn", "stage_ids": [11], "extras": ["RSQ", "RMQ", "Lazy propagation", "Sparse table", "LCA"]},
    {"title": "Đồ thị", "stage_ids": [9, 10], "extras": ["Topological sort", "Strongly connected components", "Euler tour", "Network flow"]},
    {"title": "Toán rời rạc và lý thuyết số", "stage_ids": [12], "extras": ["Sieve of Eratosthenes", "Fast exponentiation", "Chinese remainder theorem"]},
    {"title": "Chuỗi và xử lý văn bản", "stage_ids": [13], "extras": ["Suffix array", "Suffix automaton", "Aho-Corasick"]},
    {"title": "Cấu trúc dữ liệu nâng cao", "stage_ids": [], "extras": ["Disjoint Sparse Table", "Treap", "Sqrt decomposition", "Heavy-Light Decomposition", "Persistent Segment Tree"]},
    {"title": "Luyện thi tổng hợp", "stage_ids": [14], "extras": ["Upsolving", "Template cá nhân", "Chiến lược phân bổ thời gian"]},
]

def roadmap_extra_slug(title):
    normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return slug or "extra-topic"


def clean_roadmap_title(title):
    return re.sub(r"^\s*\d+(?:\.\d+)+(?:\.|\))?\s*", "", title or "").strip()


def roadmap_title_key(title):
    cleaned = clean_roadmap_title(title).lower()
    cleaned = re.sub(r"[^a-z0-9À-ỹ]+", " ", cleaned, flags=re.IGNORECASE).strip()
    return re.sub(r"\s+", " ", cleaned)


def roadmap_extra_file(slug):
    return os.path.join(settings.BASE_DIR, "oj", "roadmap_data", "topics", "extra", f"{slug}.html")


def build_roadmap_chapters(stages):
    stage_by_id = {stage["id"]: stage for stage in stages}
    chapters = []
    topic_total = 0
    for chapter_index, chapter in enumerate(ROADMAP_CHAPTERS, start=1):
        lessons = []
        seen_titles = set()
        topic_number = 1
        for stage_id in chapter["stage_ids"]:
            stage = stage_by_id.get(stage_id)
            if not stage:
                continue
            for lesson_index, topic in enumerate(stage.get("topics", []), start=1):
                raw_title = topic.get("title", "")
                title = clean_roadmap_title(raw_title)
                title_key = roadmap_title_key(title)
                if title_key in seen_titles:
                    continue
                seen_titles.add(title_key)
                topic_type = "Bài tập" if any(k in title.lower() for k in ["solver", "bài", "n-queens", "sudoku"]) else ("Ví dụ" if topic.get("sample_cpp") or topic.get("sample_py") else "Lý thuyết")
                lessons.append({
                    "number": f"{chapter_index}.{topic_number}",
                    "title": title,
                    "summary": topic.get("summary", ""),
                    "type": topic_type,
                    "status_key": f"roadmap-{stage_id}-{lesson_index}",
                    "slug": "",
                    "url": f"/roadmap/stage/{stage_id}/topic/{lesson_index}/",
                    "source": "lesson",
                })
                topic_number += 1
        for extra in chapter.get("extras", []):
            title = clean_roadmap_title(extra)
            title_key = roadmap_title_key(title)
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            slug = roadmap_extra_slug(title)
            lessons.append({
                "number": f"{chapter_index}.{topic_number}",
                "title": title,
                "summary": "",
                "type": "Bổ sung",
                "status_key": f"roadmap-extra-{slug}",
                "slug": slug,
                "url": f"/roadmap/extra/{slug}/",
                "source": "extra",
            })
            topic_number += 1
        topic_total += len(lessons)
        chapters.append({
            "index": chapter_index,
            "title": chapter["title"],
            "lessons": lessons,
            "lesson_count": len(lessons),
        })
    return chapters, topic_total


def roadmap_extra_topic(request, slug):
    title = None
    for chapter in ROADMAP_CHAPTERS:
        for extra in chapter.get("extras", []):
            if roadmap_extra_slug(extra) == slug:
                title = extra
                break
        if title:
            break
    if not title:
        return render(request, "oj/not_found.html", {"message": "Không tìm thấy nội dung bổ sung."})

    html_path = roadmap_extra_file(slug)
    if not os.path.exists(html_path):
        detail = f"<p class='text-danger'>⚠️ Không tìm thấy file nội dung: <code>{html.escape(html_path)}</code></p>"
    else:
        with open(html_path, "r", encoding="utf-8", errors="replace") as f:
            detail = f.read()

    return render(request, "roadmap_detail.html", {
        "stage": {"id": "extra", "title": "Nội dung bổ sung"},
        "topic": {"title": title, "summary": "", "detail": detail},
    })

# ==============================
# 🏠 HOME
# ==============================
def home(request):
    leaderboard = LearningLeaderboardService().compute(top_n=10)
    roadmap_chapters, roadmap_topic_count = build_roadmap_chapters(STAGES)
    return render(request, "home.html", {
        "stages": STAGES,
        "roadmap_chapters": roadmap_chapters,
        "roadmap_chapter_count": len(roadmap_chapters),
        "roadmap_topic_count": roadmap_topic_count,
        "learning_leaderboard": leaderboard,
    })


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
