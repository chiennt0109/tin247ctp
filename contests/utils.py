# path: contests/utils.py
from django.db.models import Max
from contests.models import Contest, Participation
from submissions.models import Submission

def update_participation(user, problem):
    """Cập nhật điểm và penalty của người dùng trong contest chứa problem đó."""

    # Xác định contest nào chứa problem này
    contests = Contest.objects.filter(problems=problem)

    for contest in contests:
        # lấy (hoặc tạo) bản ghi Participation
        part, _ = Participation.objects.get_or_create(user=user, contest=contest)

        # các bài trong contest
        contest_problems = list(contest.problems.all())

        # đếm số bài AC khác nhau
        ac_count = (
            Submission.objects.filter(
                user=user, problem__in=contest_problems, verdict="Accepted"
            )
            .values("problem")
            .distinct()
            .count()
        )

        # đếm số lần Wrong Answer
        wrong_count = Submission.objects.filter(
            user=user, problem__in=contest_problems, verdict="Wrong Answer"
        ).count()

        # thời điểm nộp gần nhất
        last_submit = (
            Submission.objects.filter(user=user, problem__in=contest_problems)
            .aggregate(last=Max("created_at"))["last"]
        )

        # ✅ Cập nhật Participation
        part.score = ac_count * 100
        part.penalty = wrong_count * 10
        if last_submit:
            part.last_submit = last_submit
        part.save(update_fields=["score", "penalty", "last_submit"])
