# path: problems/views_admin.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
import json

@csrf_exempt
@staff_member_required
def ai_suggest_tags(request):
    """
    API rất nhỏ cho admin:
    - input: { "statement": "...đề bài thô..." }
    - output: { "tags": ["Graph", "Dijkstra", ...] }

    Hiện tại dùng rule-based (tầng 0, miễn phí).
    Sau này bạn có thể thay bằng model AI thật.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        body = {}

    text = (body.get("statement") or "").lower()

    suggested = []

    # --- Heuristic gợi ý tag ---
    if any(k in text for k in ["đồ thị", "graph", "cạnh", "đỉnh"]):
        suggested.append("Graph")
    if any(k in text for k in ["bfs", "dfs", "dijkstra", "shortest path", "đường đi ngắn nhất", "chi phí thấp nhất"]):
        suggested.append("Shortest Path")
    if any(k in text for k in ["quy hoạch động", "quy hoach dong", "dynamic programming", "dp", "f[i]"]):
        suggested.append("DP")
    if any(k in text for k in ["chuỗi", "xâu", "string", "substring", "prefix", "kmp", "z-algorithm"]):
        suggested.append("String")
    if any(k in text for k in ["tham lam", "tham-lam", "greedy"]):
        suggested.append("Greedy")
    if any(k in text for k in ["hai con trỏ", "two pointers", "two-pointer", "two pointer"]):
        suggested.append("Two Pointers")
    if any(k in text for k in ["sắp xếp", "sort", "sorting"]):
        suggested.append("Sorting")
    if any(k in text for k in ["cây phân đoạn", "segment tree", "fenwick", "binary indexed tree", "bit tree"]):
        suggested.append("Data Structure")

    if any(k in text for k in ["mod", "modulo", "ước", "bội", "gcd", "lcm", "số nguyên tố", "prime"]):
        suggested.append("Math")

    # fallback nếu rỗng
    if not suggested:
        suggested.append("General")

    # loại trùng, giữ thứ tự
    seen = set()
    unique_tags = []
    for t in suggested:
        if t not in seen:
            seen.add(t)
            unique_tags.append(t)

    return JsonResponse({"tags": unique_tags})
