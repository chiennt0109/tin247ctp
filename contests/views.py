from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from .models import Contest, Participation
from django.db.models import Count, Q, Min, Max
from submissions.models import Submission
from .ai_analysis import analyze_user_performance


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
    contest_problems = list(contest.problems.all())

    # ✅ Cập nhật điểm, penalty, và thời gian nộp gần nhất
    for part in Participation.objects.filter(contest=contest).select_related("user"):
        ac_count = (
            Submission.objects.filter(
                user=part.user,
                problem__in=contest_problems,
                verdict="Accepted"
            )
            .values("problem")
            .distinct()
            .count()
        )

        wrong_count = Submission.objects.filter(
            user=part.user,
            problem__in=contest_problems,
            verdict="Wrong Answer"
        ).count()

        # ⚠️ Dùng created_at thay cho submit_time
        last_submit = (
            Submission.objects.filter(
                user=part.user,
                problem__in=contest_problems
            )
            .aggregate(last=Max("created_at"))["last"]
        )

        part.score = ac_count * 100
        part.penalty = wrong_count * 10
        if last_submit:
            part.last_submit = last_submit
        part.save(update_fields=["score", "penalty", "last_submit"])

    # ✅ Xếp hạng
    rankings = (
        Participation.objects.filter(contest=contest)
        .select_related("user")
        .order_by("-score", "penalty", "last_submit")
    )

    return render(
        request,
        "contests/rank.html",
        {
            "contest": contest,
            "rankings": rankings,
            "total_problems": total_problems,
        },
    )


def contest_ai_report(request, contest_id):
    contest = get_object_or_404(Contest, pk=contest_id)
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Bạn cần đăng nhập để xem phân tích."}, status=403)

    report = analyze_user_performance(request.user, contest)
    return JsonResponse(report)


