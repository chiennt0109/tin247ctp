from django.shortcuts import render, get_object_or_404
from .models import Contest  # tên model của bạn

def contest_list(request):
    contests = Contest.objects.all().order_by('-start_time') if hasattr(Contest, 'start_time') else Contest.objects.all()
    return render(request, "contests/list.html", {
        "contests": contests
    })

def contest_detail(request, contest_id):
    contest = get_object_or_404(Contest, pk=contest_id)
    return render(request, "contests/detail.html", {
        "contest": contest
    })

def contest_rank(request, contest_id):
    contest = get_object_or_404(Contest, pk=contest_id)
    rankings = []  # tạm thời để không lỗi
    return render(request, "contests/rank.html", {
        "contest": contest,
        "rankings": rankings
    })
