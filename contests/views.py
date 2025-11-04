from django.shortcuts import render, get_object_or_404
from .models import Contest
from django.utils import timezone

def contest_list(request):
    now = timezone.now()
    contests = Contest.objects.all().order_by("-start_time")

    for c in contests:
        if c.start_time > now:
            c.status = "upcoming"
        elif c.end_time and c.end_time < now:
            c.status = "finished"
        else:
            c.status = "running"

    return render(request, "contests/list.html", {"contests": contests})

def contest_rank(request, contest_id):
    contest = get_object_or_404(Contest, pk=contest_id)

    # TODO: sau này kéo bảng điểm từ DB submissions
    rankings = []  # tạm thời để trống, tránh lỗi

    return render(request, "contests/rank.html", {
        "contest": contest,
        "rankings": rankings
    })
