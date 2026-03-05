from submissions.models import Submission
from problems.models import Problem
from problems.ai_helper import build_learning_path
from django.db.models import Count, Q

def analyze_user_performance(user, contest):
    """Phân tích cá nhân hoá kết quả người dùng trong contest."""
    subs = Submission.objects.filter(user=user, problem__in=contest.problems.all())

    total = subs.values("problem").distinct().count()
    ac_count = subs.filter(verdict="Accepted").values("problem").distinct().count()
    wrong_count = subs.filter(~Q(verdict="Accepted")).count()

    # Ước lượng độ khó trung bình người dùng đã làm tốt
    probs = subs.filter(verdict="Accepted").select_related("problem")
    if probs.exists():
        levels = {"Easy": 1, "Medium": 2, "Hard": 3}
        avg = sum(levels.get(p.problem.difficulty, 1) for p in probs) / probs.count()
        diff = "Easy" if avg < 1.5 else "Medium" if avg < 2.5 else "Hard"
    else:
        diff = "Easy"

    path = build_learning_path(user, ac_count, diff)

    return {
        "summary": f"Bạn đã giải đúng {ac_count}/{total} bài trong contest này.",
        "wrong_subs": wrong_count,
        "ai_path": path["recommendations"],
    }
