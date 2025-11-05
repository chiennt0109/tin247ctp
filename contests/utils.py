from .models import Participation, Contest
from submissions.models import Submission
from django.utils import timezone

def update_participation(user, problem):
    """Khi người dùng nộp bài, tự động cập nhật điểm vào Participation."""
    # Tìm contest chứa problem này
    contests = Contest.objects.filter(problems=problem)
    for contest in contests:
        part, _ = Participation.objects.get_or_create(contest=contest, user=user)

        # Đếm số bài đã AC trong contest
        ac_count = Submission.objects.filter(
            user=user, problem__in=contest.problems.all(), verdict="Accepted"
        ).count()

        # Tổng điểm = 100 * số bài AC
        part.score = ac_count * 100
        part.last_submit = timezone.now()

        # Phạt (penalty) = số lần nộp sai trước khi AC
        wrong_count = Submission.objects.filter(
            user=user, problem__in=contest.problems.all(), verdict="Wrong Answer"
        ).count()
        part.penalty = wrong_count * 10

        part.save()
