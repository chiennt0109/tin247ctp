from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from .models import Contest, Participation
from django.db.models import Count
from submissions.models import Submission

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
    total_problems = contest.problems.count()

    # cập nhật tự động điểm và bài AC
    for part in Participation.objects.filter(contest=contest).select_related("user"):
        ac_count = Submission.objects.filter(
            user=part.user, problem__in=contest.problems.all(), verdict="Accepted"
        ).values("problem").distinct().count()
        wrong_count = Submission.objects.filter(
            user=part.user, problem__in=contest.problems.all(), verdict="Wrong Answer"
        ).count()
        part.score = ac_count * 100
        part.penalty = wrong_count * 10
        part.save()

    rankings = (
        Participation.objects.filter(contest=contest)
        .select_related("user")
        .order_by("-score", "penalty", "last_submit")
    )

    return render(request, "contests/rank.html", {
        "contest": contest,
        "rankings": rankings,
        "total_problems": total_problems,
    })

