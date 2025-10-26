# path: problems/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Problem, Tag
import random
from .ai_helper import gen_ai_hint, analyze_failed_test, recommend_next
from .ai_helper import build_learning_path
from submissions.models import Submission
from .models import Problem
from .ai.ai_hint import get_hint

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
# 🤖 Gợi ý thông minh
def ai_hint_real(request, pk):
    from .models import Problem
    p = get_object_or_404(Problem, pk=pk)
    hint = gen_ai_hint(p.statement, p.difficulty)
    return JsonResponse({"type": "hint", "result": hint})


# 🧪 Giải thích lỗi test
def ai_debug(request, pk):
    input_data = request.GET.get("input", "")
    expected = request.GET.get("expected", "")
    got = request.GET.get("got", "")
    result = analyze_failed_test(input_data, expected, got)
    return JsonResponse({"type": "debug", "result": result})


# 🧭 Gợi ý bài tiếp theo
def ai_recommend(request, pk):
    from .models import Problem
    p = get_object_or_404(Problem, pk=pk)
    result = recommend_next(p.difficulty)
    return JsonResponse({"type": "recommend", "result": result})



def ai_learning_path(request):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"error": "Bạn cần đăng nhập để xem lộ trình."}, status=403)
    
    subs = Submission.objects.filter(user=user)
    solved = subs.filter(verdict="AC").count()

    if solved == 0:
        return JsonResponse({"summary": "Bạn chưa có bài nào đúng 😅", "recommendations": [
            "🔰 Bắt đầu từ mục 'Giai đoạn 1' trong Roadmap.",
            "📘 Làm 3 bài Easy đầu tiên để hệ thống phân tích trình độ."
        ]})

    # Tính độ khó trung bình
    probs = [s.problem for s in subs.filter(verdict="AC")]
    levels = {"Easy": 1, "Medium": 2, "Hard": 3}
    if not probs:
        avg_difficulty = "Easy"
    else:
        avg_score = sum(levels.get(p.difficulty, 1) for p in probs) / len(probs)
        avg_difficulty = "Easy" if avg_score < 1.5 else ("Medium" if avg_score < 2.5 else "Hard")

    plan = build_learning_path(user, solved, avg_difficulty)
    return JsonResponse(plan)
def problem_list(request):
    problems = Problem.objects.all().order_by("id")
    return render(request, "problems/list.html", {"problems": problems})


def problem_detail(request, pk):
    problem = get_object_or_404(Problem, pk=pk)
    return render(request, "problems/detail.html", {"problem": problem})


# ✅ API AI Hint
def ai_hint(request, pk):
    problem = get_object_or_404(Problem, pk=pk)
    hint = get_hint(problem.title, problem.difficulty)
    return JsonResponse({"hint": hint})

