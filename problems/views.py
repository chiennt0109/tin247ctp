# path: problems/views.py
from django.shortcuts import render, get_object_or_404
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.core.paginator import Paginator
import random
from django.template.loader import render_to_string
from .models import Problem, Tag
from submissions.models import Submission
from contests.models import Contest, PracticeSession
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from .editorial_access import resolve_editorial_access
from django.contrib import messages



# AI helpers
from .ai_helper import (
    gen_ai_hint,
    analyze_failed_test,
    recommend_next,
    build_learning_path,
    recommend_next_personal,
)

# AI hint LLM
from .ai.ai_hint import get_hint

# ===========================
# 🎯 GỢI Ý BÀI THEO NGƯỜI DÙNG
# ===========================
def ai_recommend_personal(request):
    user = request.user
    res = recommend_next_personal(user)
    return JsonResponse({"result": res})

# ===========================
# 🌈 DANH SÁCH BÀI TOÁN + PAGINATION
# ===========================
# path: problems/views.py
def problem_list(request):
    tag_slug = request.GET.get("tag", "").strip()
    difficulty = request.GET.get("difficulty", "").strip()
    search_query = request.GET.get("q", "").strip()
    sort_by = request.GET.get("sort", "").strip()
    page_number = request.GET.get("page", 1)

    # --- Query cơ bản ---
    qs = Problem.objects.all().prefetch_related("tags").order_by("code")

    # --- Lọc theo tag ---
    if tag_slug:
        qs = qs.filter(tags__slug=tag_slug)

    # --- Lọc theo độ khó ---
    if difficulty:
        qs = qs.filter(difficulty__iexact=difficulty)

    # --- Tìm kiếm ---
    if search_query:
        qs = qs.filter(Q(title__icontains=search_query) | Q(code__icontains=search_query))

    # --- Sắp xếp ---
    if sort_by == "difficulty":
        qs = qs.order_by("difficulty", "code")
    elif sort_by == "popularity":
        qs = qs.order_by("-ac_count", "code")

    # --- Phân trang ---
    paginator = Paginator(qs, 15)
    problems = paginator.get_page(page_number)
    tags = Tag.objects.all().order_by("name")
    difficulty_levels = ["Easy", "Medium", "Hard"]

    # Nếu là AJAX request → trả về HTML partial
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        html = render_to_string(
            "problems/partials/_problem_table.html",
            {
                "problems": problems,
                "selected_tag": tag_slug,
            },
            request=request,
        )
        return HttpResponse(html)

    return render(request, "problems/list.html", {
        "problems": problems,
        "tags": tags,
        "difficulty_levels": difficulty_levels,
        "selected_tag": tag_slug,
        "selected_difficulty": difficulty,
        "search_query": search_query,
        "sort_by": sort_by,
    })


# ===========================
# 📘 CHI TIẾT BÀI TOÁN — phân biệt NORMAL / CONTEST / PRACTICE
# ===========================


def problem_detail(request, pk):
    problem = get_object_or_404(Problem, pk=pk)

    # ===== COMMON STATS =====
    submit_count = Submission.objects.filter(problem=problem).count()
    ac_count = Submission.objects.filter(problem=problem, verdict="Accepted").count()

    # ===== GET PARAMS =====
    contest_id = request.GET.get("contest_id")
    is_practice = request.GET.get("practice") == "1"
    view = request.GET.get("view")
    if view == "editorial":
        mode = "normal"  
        
    practice = request.GET.get("practice")
    mode = "normal"
    practice_session = None
    contest = None

    # ============================================
    # ⭐ CASE 1: PRACTICE MODE
    # ============================================
    if is_practice and contest_id:
        contest = get_object_or_404(Contest, pk=contest_id)
        request.is_practice_mode = True
        session = PracticeSession.objects.filter(
            contest=contest,
            user=request.user,
            is_started=True,
            is_locked=False,
            cancelled=False,
        ).order_by("-created_at").first()

        if not session:
            return redirect("contests:contest_practice", contest_id=contest.id)

        if session.remaining_seconds == 0:
            session.is_locked = True
            session.save(update_fields=["is_locked"])
            return redirect("contests:contest_practice", contest_id=contest.id)

        mode = "practice"
        practice_session = session
        request.is_practice_mode = True
    # ============================================
    # ⭐ CASE 2: CONTEST MODE
    # ============================================
    elif contest_id:
        contest = get_object_or_404(Contest, pk=contest_id)
    
        if timezone.now() > contest.end_time:
    
            # Nếu đang xem view=editorial → ép sang chế độ NORMAL hoàn toàn
            if request.GET.get("view") == "editorial":
                request.is_practice_mode = False

                contest = None
                mode = "normal"      # ← THÊM DÒNG NÀY
            else:
                return render(request, "submissions/contest_block.html", {
                    "contest": contest,
                    "problem": problem,
                    "error": "Cuộc thi đã kết thúc. Bạn không thể xem đề bài."
                })
    
        else:
            mode = "contest"

    # ============================================
    # ⭐ CASE 3: NORMAL MODE
    # ============================================
    else:
        request.is_practice_mode = False
        contest = None
        mode = "normal"

    # ============================================
    # EDITORIAL ACCESS
    # ============================================
    can_view, requires_payment, editorial, editorial_format = resolve_editorial_access(
        #request=request,
        user=request.user,
        problem=problem,
        contest=contest,
        is_practice=is_practice,
    )

    # ============================================
    # CONTEXT
    # ============================================
    context = {
        "problem": problem,
        "submit_count": submit_count,
        "ac_count": ac_count,
        "contest_id": contest_id,
        "mode": mode,
        "is_practice": is_practice,
        "practice_session": practice_session,
        "practice": practice,

        # editorial keys
        "can_view_editorial": can_view,
        "requires_editorial_payment": requires_payment,
        "editorial": editorial,
        "editorial_exists": editorial is not None,
        "editorial_format": editorial_format,
    }

    return render(request, "problems/detail.html", context)




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
# 🎯 Gợi ý bài kế tiếp
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
                "Làm 3 bài Easy đầu tiên",
            ],
        })

    probs = [s.problem for s in subs.filter(verdict="Accepted")]
    levels = {"Easy": 1, "Medium": 2, "Hard": 3}
    avg_score = sum(levels[p.difficulty] for p in probs) / len(probs)
    diff = "Easy" if avg_score < 1.5 else "Medium" if avg_score < 2.5 else "Hard"

    return JsonResponse(build_learning_path(user, solved, diff))

# ========== BACKWARD COMPAT fix ==========
def ai_hint(request, pk):
    return ai_hint_real(request, pk)

# ===========================
# ✅ AI TOOLS FOR ADMIN FORM
# ===========================
from django.views.decorators.csrf import csrf_exempt

def admin_ai_generate(request):
    sample_problem = (
        "### Bài toán ví dụ\n"
        "Cho dãy số A có N phần tử. Hãy in tổng các phần tử.\n\n"
        "**Input:**\nN và dãy số A\n\n"
        "**Output:**\nTổng các phần tử.\n"
    )
    return JsonResponse({"content": sample_problem})

@csrf_exempt
def admin_ai_samples(request):
    txt = request.body.decode("utf-8")
    return JsonResponse({
        "samples": [
            {"in": "3\n1 2 3", "out": "6"},
            {"in": "5\n2 2 2 2 2", "out": "10"},
        ]
    })

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


from .models import EditorialPurchase, ProblemEditorial

@login_required
def buy_editorial(request, pk):
    problem = get_object_or_404(Problem, pk=pk)
    editorial = problem.editorial_meta

    PRICE = 20  # config sau cũng được
    profile = request.user.profile

    if profile.coins < PRICE:
        messages.error(request, "Không đủ xu!")
        return redirect("problems:problem_detail", pk=pk)

    profile.coins -= PRICE
    profile.save()

    EditorialPurchase.objects.get_or_create(
        user=request.user, problem=problem
    )

    messages.success(request, "Mua lời giải thành công!")
    return redirect("problems:problem_detail", pk=pk)


def get_contest_editorial_rules(request, contest_id):
    contest = get_object_or_404(Contest, pk=contest_id)
    rules = ContestEditorialAccess.objects.filter(contest=contest)

    return JsonResponse({
        "contest": contest.name,
        "rules": [
            {
                "problem": r.problem.code,
                "mode": r.mode,
                "display": r.get_mode_display()
            }
            for r in rules
        ]
    })
