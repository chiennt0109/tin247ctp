# path: problems/views.py
from django.shortcuts import render, get_object_or_404
from .models import Problem, Tag

def problem_list(request):
    problems = Problem.objects.all()

    # Bộ lọc đơn giản
    difficulty = request.GET.get('difficulty')
    tag = request.GET.get('tag')

    if difficulty:
        problems = problems.filter(difficulty=difficulty)
    if tag:
        problems = problems.filter(tags__slug=tag)

    context = {
        'problems': problems.order_by('code'),
        'tags': Tag.objects.all(),
        'selected_difficulty': difficulty,
        'selected_tag': tag,
    }
    return render(request, 'problems/list.html', context)


def problem_detail(request, pk):
    problem = get_object_or_404(Problem, pk=pk)
    return render(request, 'problems/detail.html', {'p': problem})
