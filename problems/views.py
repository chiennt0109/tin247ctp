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
    return render(request, "problems/list.html", {
        "problems": problems,
        "tags": tags,
        "selected_tag": tag_slug,
        "selected_difficulty": difficulty,
    })

def problem_detail(request, pk):
    p = get_object_or_404(Problem, pk=pk)
    return render(request, "problems/detail.html", {"p": p})
