# path: problems/views.py
from django.shortcuts import render, get_object_or_404
from .models import Problem, Tag

def problem_list(request):
    tag_slug = request.GET.get("tag")
    difficulty = request.GET.get("difficulty")

    problems = Problem.objects.all().prefetch_related("tags")

    if tag_slug:
        problems = problems.filter(tags__slug=tag_slug)
    if difficulty:
        problems = problems.filter(difficulty=difficulty)

    tags = Tag.objects.all().order_by("name")
    difficulty_levels = ["Easy", "Medium", "Hard"]  # ✅ thêm dòng này

    return render(request, "problems/list.html", {
        "problems": problems,
        "tags": tags,
        "difficulty_levels": difficulty_levels,  # ✅ gửi sang template
        "selected_tag": tag_slug,
        "selected_difficulty": difficulty,
    })
