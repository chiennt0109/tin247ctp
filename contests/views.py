from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from .models import Contest  # tên model của bạn

def contest_list(request):
    contests = Contest.objects.all().order_by('-start_time')
    now = timezone.now()
    return render(request, "contests/list.html", {
        "contests": contests,
        "now": now,
    })

def contest_detail(request, contest_id):
    contest = get_object_or_404(Contest, pk=contest_id)
    problems = contest.problems.all().order_by("code")  # Lấy bài trong contest
    return render(request, "contests/detail.html", {
        "contest": contest,
        "problems": problems,
    })

def contest_rank(request, contest_id):
    contest = get_object_or_404(Contest, pk=contest_id)
    rankings = []  # tạm thời để không lỗi
    return render(request, "contests/rank.html", {
        "contest": contest,
        "rankings": rankings
    })
