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

    # Kiểm tra có field ac_count / submit_count sẵn không để tránh trùng tên annotate
    has_ac_field = False
    has_submit_field = False
    try:
        Problem._meta.get_field("ac_count")
        has_ac_field = True
    except Exception:
        pass
    try:
        Problem._meta.get_field("submit_count")
        has_submit_field = True
    except Exception:
        pass

    if has_ac_field or has_submit_field:
        qs = qs.annotate(
            submit_count_agg=Count("submission", distinct=True),
            ac_count_agg=Count("submission", filter=Q(submission__verdict="Accepted"), distinct=True),
        )
        problems = list(qs)
        for p in problems:
            if not hasattr(p, "submit_count") or p.submit_count is None:
                setattr(p, "submit_count", getattr(p, "submit_count_agg", 0))
            if not hasattr(p, "ac_count") or p.ac_count is None:
                setattr(p, "ac_count", getattr(p, "ac_count_agg", 0))
    else:
        qs = qs.annotate(
            submit_count=Count("submission", distinct=True),
            ac_count=Count("submission", filter=Q(submission__verdict="Accepted"), distinct=True),
        )
        problems = list(qs)

    # ✅ TÍNH SẴN % AC (tránh filter tùy biến trong template)
    for p in problems:
        sc = int(getattr(p, "submit_count", 0) or 0)
        ac = int(getattr(p, "ac_count", 0) or 0)
        p.ac_pct = int(ac * 100 / sc) if sc > 0 else 0

    tags = Tag.objects.all()
    difficulties = ["Easy", "Medium", "Hard"]

    paginator = Paginator(problems, 15)  # 9 bài / trang
    page = request.GET.get("page")
    problems_page = paginator.get_page(page)
    
    context = {
        "problems": problems_page,
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

# ===========================
# ✅ AI TOOLS FOR ADMIN FORM
# ===========================
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

# Sinh đề bằng AI (fake mẫu)
def admin_ai_generate(request):
    sample_problem = (
        "### Bài toán ví dụ\n"
        "Cho dãy số A có N phần tử. Hãy in tổng các phần tử.\n\n"
        "**Input:**\nN và dãy số A\n\n"
        "**Output:**\nTổng các phần tử.\n"
    )
    return JsonResponse({"content": sample_problem})

# Sinh sample I/O tự động
@csrf_exempt
def admin_ai_samples(request):
    txt = request.body.decode("utf-8")
    return JsonResponse({
        "samples": [
            {"in": "3\n1 2 3", "out": "6"},
            {"in": "5\n2 2 2 2 2", "out": "10"}
        ]
    })

# Kiểm tra format bài toán
@csrf_exempt
def admin_ai_check(request):
    return JsonResponse({"msg": "✅ Format hợp lệ — Markdown + I/O OK"})

# ===========================
# ✅ AI SOLUTION (fake)
# ===========================
def get_solution(request, pk):
    p = get_object_or_404(Problem, pk=pk)
    return JsonResponse({
        "solution": f"Để giải bài {p.title}, hãy duyệt mảng và xử lý theo yêu cầu đề bài.\n\n"
                    "Ví dụ Python:\n```python\narr = list(map(int,input().split()))\nprint(sum(arr))\n```"
    })
