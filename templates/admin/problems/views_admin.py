# path: problems/views_admin.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def ai_suggest_tags(request):
    """Phân tích statement và đề xuất tag cơ bản."""
    try:
        data = json.loads(request.body)
        text = data.get("statement", "").lower()
        tags = []

        if "đồ thị" in text or "graph" in text:
            tags.append("Graph")
        if "dijkstra" in text:
            tags.append("Dijkstra")
        if "dfs" in text or "bfs" in text:
            tags.append("Graph Traversal")
        if "dynamic" in text or "quy hoạch" in text:
            tags.append("DP")
        if "sort" in text or "sắp xếp" in text:
            tags.append("Sorting")
        if "binary search" in text or "nhị phân" in text:
            tags.append("Binary Search")
        if "string" in text or "chuỗi" in text:
            tags.append("String")
        if not tags:
            tags.append("General")

        return JsonResponse({"tags": tags})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
