# path: problems/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Count, Q
from django.core.paginator import Paginator
import random

from .models import Problem, Tag
from submissions.models import Submission

# AI helpers
from .ai_helper import (
    gen_ai_hint,
    analyze_failed_test,
    recommend_next,
    build_learning_path,
)

# AI hint LLM
from .ai.ai_hint import get_hint


# ===========================
# 🌈 DANH SÁCH BÀI TOÁN + PAGINATION
# ===========================
def problem_list(request):
    tag_slug = request.GET.get("tag", "").strip()
    difficulty = request.GET.get("difficulty", "").strip()

    qs = Problem.objects.all().order_by("code")

    if tag_slug:
        qs = qs.filter(tags__slug=tag_slug)
    if difficulty:
        qs = qs.filter(difficulty=difficulty)

    qs = qs.annotate(
        submit_count_live=Count("submission", distinct=True),
        ac_count_live=Count(
            "submission",
            filter=Q(submission__verdict="Accepted"),
            distinct=True,
        ),
    )

    paginator = Paginator(qs, 12)  # ✅ mỗi trang 12 bài
    page = request.GET.get("page")
    problems = paginator.get_page(page)

    return render(
        request,
        "problems/list.html",
        {
            "problems": problems,
            "tags": Tag.objects.all(),
            "difficulty_levels": ["Easy", "Medium", "Hard"],
            "selected_tag": tag_slug,
            "selected_difficulty": difficulty,
        },
    )


# ===========================
# 📘 CHI TIẾT BÀI TOÁN
# ===========================
def problem_detail(request, pk):
    problem = get_object_or_404(Problem, pk=pk)
    submit_count = Submission.objects.filter(problem=problem).count()
    ac_count = Submission.objects.filter(problem=problem, verdict="Accepted").count()

    return render(
        request,
        "problems/detail.html",
        {
            "problem": problem,
            "submit_count": submit_count,
            "ac_count": ac_count,
        },
    )


# ===========================
# 🤖 AI HINT: bản random cũ
# ===========================
AI_HINTS = [
    "Thử kiểm tra lại điều kiện dừng của vòng lặp.",
    "Hãy xem xét các trường hợp biên.",
    "Dùng prefix sum hoặc DP xem sao?",
    "Cẩn thận tràn số — dùng long long.",
    "Kiểm tra lại input format.",
    "Reset biến giữa các test case.",
]

def ai_hint_random(request, pk):
    return JsonResponse({"result": random.choice(AI_HINTS)})


# ===========================
# 🤖 AI hint LLM chính
# ===========================
def ai_hint_real(request, pk):
    problem = get_object_or_404(Problem, pk=pk)
    hint = get_hint(problem.title, problem.difficulty)
    return JsonResponse({"result": hint})


# ===========================
# 🧪 AI debug test fail
# ===========================
def ai_debug(request, pk):
    input_data = request.GET.get("input", "")
    expected = request.GET.get("expected", "")
    got = request.GET.get("got", "")
    res = analyze_failed_test(input_data, expected, got)
    return JsonResponse({"result": res})


# ===========================
# 🎯 Gợi ý bài kế
# ===========================
def ai_recommend(request, pk):
    p = get_object_or_404(Problem, pk=pk)
    res = recommend_next(p.difficulty)
    return JsonResponse({"result": res})


# ===========================
# 📚 AI lộ trình học
# ===========================
def ai_learning_path(request):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"result": "Bạn cần đăng nhập để xem lộ trình."}, status=403)

    subs = Submission.objects.filter(user=user)
    solved = subs.filter(verdict="Accepted").count()

    if solved == 0:
        return JsonResponse({
            "summary": "Bạn chưa giải bài nào.",
            "suggest": [
                "Bắt đầu từ Roadmap Giai đoạn 1",
                "Làm 3 bài Easy đầu tiên"
            ]
        })

    probs = [s.problem for s in subs.filter(verdict="Accepted")]
    levels = {"Easy": 1, "Medium": 2, "Hard": 3}
    avg_score = sum(levels[p.difficulty] for p in probs) / len(probs)
    diff = "Easy" if avg_score < 1.5 else "Medium" if avg_score < 2.5 else "Hard"

    return JsonResponse(build_learning_path(user, solved, diff))

# ========== BACKWARD COMPAT fix ==========
# Giúp URL cũ ai_hint/ vẫn hoạt động
def ai_hint(request, pk):
    return ai_hint_real(request, pk)

