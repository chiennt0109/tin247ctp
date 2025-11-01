# path: problems/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Count, Q
from .models import Problem, Tag
import random

from submissions.models import Submission
from .ai_helper import gen_ai_hint, analyze_failed_test, recommend_next, build_learning_path
from .ai.ai_hint import get_hint

# ===========================
# 🌈 DANH SÁCH BÀI TOÁN
# ===========================
def problem_list(request):
    tag_slug = request.GET.get("tag", "").strip()
    difficulty = request.GET.get("difficulty", "").strip()

    qs = Problem.objects.all().order_by("code")

    if tag_slug:
        qs = qs.filter(tags__slug=tag_slug)

    if difficulty:
        qs = qs.filter(difficulty=difficulty)

    # ✅ Thống kê submit/AC
    qs = qs.annotate(
        submit_count = Count("submission", distinct=True),
        ac_count = Count("submission", filter=Q(submission__verdict="Accepted"), distinct=True),
    )

    tags = Tag.objects.all()
    difficulties = ["Easy", "Medium", "Hard"]

    context = {
        "problems": qs,
        "tags": tags,
        "difficulty_levels": difficulties,
        "selected_tag": tag_slug,
        "selected_difficulty": difficulty,
    }
    return render(request, "problems/list.html", context)


# ===========================
# 📘 CHI TIẾT BÀI TOÁN
# ===========================
def problem_detail(request, pk):
    problem = get_object_or_404(Problem, pk=pk)

    submit_count = Submission.objects.filter(problem=problem).count()
    ac_count = Submission.objects.filter(problem=problem, verdict="Accepted").count()

    return render(request, "problems/detail.html", {
        "problem": problem,
        "submit_count": submit_count,
        "ac_count": ac_count,
    })


# ===========================
# 🤖 AI gợi ý (random)
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
    return JsonResponse({"hint": random.choice(AI_HINTS)})


# ✅ AI hint thật
def ai_hint_real(request, pk):
    p = get_object_or_404(Problem, pk=pk)
    return JsonResponse({"type": "hint", "result": gen_ai_hint(p.statement, p.difficulty)})


# ✅ AI giải thích test sai
def ai_debug(request, pk):
    input_data = request.GET.get("input", "")
    expected = request.GET.get("expected", "")
    got = request.GET.get("got", "")
    return JsonResponse({"type": "debug", "result": analyze_failed_test(input_data, expected, got)})


# ✅ AI gợi ý bài kế tiếp
def ai_recommend(request, pk):
    p = get_object_or_404(Problem, pk=pk)
    return JsonResponse({"type": "recommend", "result": recommend_next(p.difficulty)})


# ✅ Lộ trình học AI
def ai_learning_path(request):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"error": "Bạn cần đăng nhập để xem lộ trình."}, status=403)

    subs = Submission.objects.filter(user=user)
    solved = subs.filter(verdict="Accepted").count()

    if solved == 0:
        return JsonResponse({
            "summary": "Bạn chưa có bài nào đúng 😅",
            "recommendations": [
                "🔰 Bắt đầu từ mục 'Giai đoạn 1' trong Roadmap.",
                "📘 Làm 3 bài Easy đầu tiên để hệ thống phân tích trình độ."
            ]
        })

    probs = [s.problem for s in subs.filter(verdict="Accepted")]
    levels = {"Easy": 1, "Medium": 2, "Hard": 3}

    if not probs:
        avg_difficulty = "Easy"
    else:
        avg_score = sum(levels.get(p.difficulty, 1) for p in probs) / len(probs)
        avg_difficulty = "Easy" if avg_score < 1.5 else ("Medium" if avg_score < 2.5 else "Hard")

    return JsonResponse(build_learning_path(user, solved, avg_difficulty))


# ✅ AI Hint chính xác
def ai_hint(request, pk):
    problem = get_object_or_404(Problem, pk=pk)
    return JsonResponse({"hint": get_hint(problem.title, problem.difficulty)})
