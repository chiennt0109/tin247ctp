# path: problems/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Problem, Tag
import random

# ===========================
# 🌈 DANH SÁCH BÀI TOÁN
# ===========================
def problem_list(request):
    problems = Problem.objects.all().order_by("code")
    tags = Tag.objects.all()

    selected_tag = request.GET.get("tag")
    selected_difficulty = request.GET.get("difficulty")

    if selected_tag:
        problems = problems.filter(tags__slug=selected_tag)
    if selected_difficulty:
        problems = problems.filter(difficulty=selected_difficulty)

    context = {
        "problems": problems,
        "tags": tags,
        "selected_tag": selected_tag,
        "selected_difficulty": selected_difficulty,
        "difficulty_levels": ["Easy", "Medium", "Hard"],
    }
    return render(request, "problems/list.html", context)


# ===========================
# 📘 CHI TIẾT MỘT BÀI TOÁN
# ===========================
def problem_detail(request, pk):
    p = get_object_or_404(Problem, pk=pk)
    return render(request, "problems/detail.html", {"p": p})


# ===========================
# 🤖 GỢI Ý TỪ AI (TẠM NGẪU NHIÊN)
# ===========================
AI_HINTS = [
    "Thử kiểm tra lại điều kiện dừng của vòng lặp.",
    "Hãy xem xét các trường hợp biên như n = 1 hoặc m = 0.",
    "Độ phức tạp O(n²) có thể gây TLE, thử tối ưu hơn bằng cấu trúc dữ liệu.",
    "Cẩn thận tràn số — dùng kiểu long long hoặc int64.",
    "Có thể bạn đang đọc input sai định dạng, hãy kiểm tra lại mẫu input.",
    "Đừng quên reset biến đếm trong mỗi test case.",
    "Khi kết quả bị lệch 1 đơn vị, hãy kiểm tra lại chỉ số mảng bắt đầu từ 0 hay 1.",
    "Hãy thử in debug với test nhỏ để kiểm tra từng bước tính toán.",
]

def ai_hint(request, pk):
    """Trả về 1 gợi ý đơn giản — sẽ được thay thế bằng gợi ý AI thật ở Phase 3."""
    hint = random.choice(AI_HINTS)
    return JsonResponse({"hint": hint})
