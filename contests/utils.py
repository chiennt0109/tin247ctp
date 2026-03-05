# path: contests/utils.py
from django.db.models import Max
from contests.models import Contest, Participation
from submissions.models import Submission


def update_participation(user, problem, contest=None):
    """
    Cập nhật Participation cho user trong contest.
    Hỗ trợ cả kiểu cũ (không có tham số contest) và kiểu mới (có contest).
    """

    # 🟦 Nếu submission KHÔNG thuộc contest → bỏ qua (normal / practice)
    if contest is None:
        # Giữ backward compatibility (logic cũ)
        contests = Contest.objects.filter(problems=problem)
    else:
        contests = [contest]

    for ct in contests:

        # 🟩 Lấy participation
        part, _ = Participation.objects.get_or_create(
            user=user,
            contest=ct
        )

        contest_problems = list(ct.problems.all())

        # =============================
        # ⭐ Tính điểm kiểu cũ của bạn
        # =============================
        # AC * 100
        ac_count = (
            Submission.objects.filter(
                user=user, problem__in=contest_problems, verdict="Accepted"
            )
            .values("problem")
            .distinct()
            .count()
        )

        # Wrong Answer * 10
        wrong_count = Submission.objects.filter(
            user=user, problem__in=contest_problems, verdict="Wrong Answer"
        ).count()

        # Lần nộp gần nhất
        last_submit = (
            Submission.objects.filter(user=user, problem__in=contest_problems)
            .aggregate(last=Max("created_at"))["last"]
        )

        # =============================
        # ⭐ Cập nhật Participation
        # =============================
        part.score = ac_count * 100
        part.penalty = wrong_count * 10
        if last_submit:
            part.last_submit = last_submit

        part.save(update_fields=["score", "penalty", "last_submit"])
