from django.shortcuts import render, get_object_or_404
from django.db.models import Sum, Count, Min
from submissions.models import Submission
from .models import Contest

def contest_list(request):
    return render(request, 'contests/list.html', { 'contests': Contest.objects.all() })

def contest_detail(request, contest_id):
    c = get_object_or_404(Contest, id=contest_id)
    return render(request, 'contests/detail.html', { 'contest': c })

def contest_rank(request, contest_id):
    c = get_object_or_404(Contest, id=contest_id)
    # Score = number of Accepted submissions per user within contest problems
    qs = (Submission.objects
          .filter(problem__in=c.problems.all(), verdict='Accepted')
          .values('user__username')
          .annotate(score=Count('id'), total_time=Sum('exec_time'))
          .order_by('-score', 'total_time'))
    return render(request, 'contests/rank.html', { 'contest': c, 'ranks': qs })
