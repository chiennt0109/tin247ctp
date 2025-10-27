# path: problems/views_admin.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
import json, re

@csrf_exempt
@staff_member_required
def ai_analyze_problem(request):
    """Phân tích đề bài: tự sinh mã, độ khó, tag."""
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        body = json.loads(request.body.decode("utf-8"))
        text = (body.get("statement") or "").lower()
        title = body.get("title") or "Untitled"
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # === 1️⃣ Gợi ý tag (rule-based) ===
    tags = []
    if any(k in text for k in ["graph", "đồ thị", "cạnh", "đỉnh"]): tags.append("Graph")
    if any(k in text for k in ["dijkstra", "bfs", "dfs", "đường đi"]): tags.append("Shortest Path")
    if any(k in text for k in ["dp", "quy hoạch động", "dynamic programming"]): tags.append("DP")
    if any(k in text for k in ["string", "xâu", "chuỗi"]): tags.append("String")
    if any(k in text for k in ["greedy", "tham lam"]): tags.append("Greedy")
    if any(k in text for k in ["sort", "sắp xếp"]): tags.append("Sorting")
    if any(k in text for k in ["mod", "gcd", "lcm", "prime", "số nguyên tố"]): tags.append("Math")
    if not tags: tags = ["General"]

    # === 2️⃣ Sinh mã bài ===
    prefix = f"{len(title)}{len(tags)}"
    keyword = re.sub(r'[^A-Za-z0-9]+', '', title.split()[0].upper())[:3]
    code = f"{prefix}-{keyword}"

    # === 3️⃣ Đánh giá độ khó ===
    difficulty = "Easy"
    if any(k in text for k in ["qhd", "dp", "dijkstra", "segment", "tổ hợp", "backtrack"]):
        difficulty = "Hard"
    elif any(k in text for k in ["greedy", "sắp xếp", "sort", "trung bình"]):
        difficulty = "Medium"
    if len(text) > 1500 or "ràng buộc" in text:
        difficulty = "Hard"

    return JsonResponse({
        "code": code,
        "difficulty": difficulty,
        "tags": tags
    })
