# path: problems/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Count, Q
from django.core.paginator import Paginator
import random
from .ai_helper import recommend_next_personal
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

def ai_recommend_personal(request):
    """
    Gợi ý bài tiếp theo dựa trên hồ sơ cá nhân.
    """
    user = request.user
    res = recommend_next_personal(user)
    return JsonResponse({"result": res})
# ===========================
# 🌈 DANH SÁCH BÀI TOÁN + PAGINATION
# ===========================
def problem_list(request):
    tag_slug = request.GET.get("tag", "").strip()
    difficulty = request.GET.get("difficulty", "").strip()
    search_query = request.GET.get("q", "").strip()
    sort_by = request.GET.get("sort", "").strip()

    qs = Problem.objects.all().order_by("code")

    # --- Lọc theo tag ---
    if tag_slug:
        qs = qs.filter(tags__slug=tag_slug)

    # --- Lọc theo độ khó ---
    if difficulty:
        qs = qs.filter(difficulty__iexact=difficulty)

    # --- Tìm kiếm theo tên bài ---
    if search_query:
        qs = qs.filter(Q(title__icontains=search_query) | Q(code__icontains=search_query))

    # --- Sắp xếp theo yêu cầu ---
    if sort_by == "difficulty":
        qs = qs.order_by("difficulty", "code")
    elif sort_by == "popularity":
        qs = qs.order_by("-ac_count", "code")

    # --- Pagination ---
    paginator = Paginator(qs, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # --- Danh sách tag & mức độ ---
    tags = Tag.objects.all().order_by("name")
    difficulty_levels = ["Easy", "Medium", "Hard"]

    return render(
        request,
        "problems/list.html",
        {
            "problems": page_obj,
            "tags": tags,
            "difficulty_levels": difficulty_levels,
            "selected_tag": tag_slug,
            "selected_difficulty": difficulty,
            "search_query": search_query,
            "sort_by": sort_by,
        },
    )

# ===========================
# 📘 CHI TIẾT BÀI TOÁN
# ===========================
def problem_detail(request, pk):
    problem = get_object_or_404(Problem, pk=pk)
    submit_count = Submission.objects.filter(problem=problem).count()
    ac_count = Submission.objects.filter(problem=problem, verdict="Accepted").count()
    contest_id = request.GET.get("contest_id")

    return render(
        request,
        "problems/detail.html",
        {
            "problem": problem,
            "submit_count": submit_count,
            "ac_count": ac_count,
            "contest_id": contest_id,  # ✅ thêm để template nhận biết
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

def get_next_recommendation(request, pk):
    return ai_recommend(request, pk)

def get_learning_path(request, pk=None):
    return ai_learning_path(request)

