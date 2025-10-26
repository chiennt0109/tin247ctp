# path: app/problems/views.py
from django.shortcuts import render, get_object_or_404
from .models import Problem, Tag


def problem_list(request):
    """
    Hiển thị danh sách bài toán với bộ lọc theo tag và độ khó.
    """
    tag_slug = request.GET.get("tag")
    difficulty = request.GET.get("difficulty")

    # Lấy toàn bộ bài toán, prefetch tags để giảm truy vấn
    problems = Problem.objects.all().prefetch_related("tags")

    # Lọc theo tag nếu có
    if tag_slug:
        problems = problems.filter(tags__slug=tag_slug)

    # Lọc theo độ khó nếu có
    if difficulty:
        problems = problems.filter(difficulty=difficulty)

    tags = Tag.objects.all().order_by("name")
    difficulty_levels = ["Easy", "Medium", "Hard"]

    context = {
        "problems": problems,
        "tags": tags,
        "difficulty_levels": difficulty_levels,
        "selected_tag": tag_slug,
        "selected_difficulty": difficulty,
    }

    return render(request, "problems/list.html", context)


def problem_detail(request, pk):
    """
    Hiển thị chi tiết một bài toán (statement, giới hạn, tag, v.v.)
    """
    problem = get_object_or_404(Problem, pk=pk)
    return render(request, "problems/detail.html", {"p": problem})
