from django.shortcuts import render, get_object_or_404
from .models import Problem

def problem_list(request):
    return render(request, 'problems/list.html', { 'problems': Problem.objects.all() })

def problem_detail(request, pk):
    p = get_object_or_404(Problem, pk=pk)
    return render(request, 'problems/detail.html', { 'p': p })
