from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from contests.models import Participation
from submissions.models import Submission

from learning_analytics.models import UserSkillStats


class LearningLeaderboardService:
    def _eligible_users(self):
        now = timezone.now()
        cutoff_90 = now - timedelta(days=90)
        cutoff_year = now - timedelta(days=365)
        users = User.objects.filter(is_staff=False, is_superuser=False, is_active=True, last_login__gte=cutoff_90)
        ids = []
        for u in users:
            total_sub = Submission.objects.filter(user=u).count()
            solved = Submission.objects.filter(user=u, verdict="Accepted").values("problem_id").distinct().count()
            if (total_sub > 1000 and solved < 1) or (u.last_login and u.last_login < cutoff_year):
                continue
            ids.append(u.id)
        return User.objects.filter(id__in=ids)

    def compute(self, top_n=10):
        now = timezone.now()
        d30 = now - timedelta(days=30)
        users = self._eligible_users()

        hardworking = []
        breakthrough = []
        needs_improvement = []

        for u in users:
            subs30 = Submission.objects.filter(user=u, created_at__gte=d30)
            submissions_30 = subs30.count()
            solved_30 = subs30.filter(verdict="Accepted").values("problem_id").distinct().count()
            login_days = subs30.datetimes("created_at", "day").count()
            activity_score = 0.5 * submissions_30 + 0.3 * solved_30 + 0.2 * login_days

            all_sub = Submission.objects.filter(user=u)
            total = all_sub.count() or 1
            accepted = all_sub.filter(verdict="Accepted").count()
            acceptance_rate = accepted / total
            failed = total - accepted

            p30 = Participation.objects.filter(user=u, contest__end_time__gte=d30)
            p60 = Participation.objects.filter(user=u, contest__end_time__gte=now - timedelta(days=60), contest__end_time__lt=d30)
            rating30 = sum((x.score * 8) - (x.penalty / 600 if x.penalty else 0) for x in p30)
            rating60 = sum((x.score * 8) - (x.penalty / 600 if x.penalty else 0) for x in p60)
            rating_growth = rating30 - rating60
            new_skills = UserSkillStats.objects.filter(user=u, updated_at__gte=d30, mastery_score__gte=60).count()
            hard_solved_30 = subs30.filter(verdict="Accepted", problem__difficulty="Hard").values("problem_id").distinct().count()
            progress_score = rating_growth + new_skills + hard_solved_30

            hardworking.append({"username": u.username, "score": round(activity_score, 2)})
            breakthrough.append({"username": u.username, "score": round(progress_score, 2)})

            if acceptance_rate < 0.2 and failed >= 10 and submissions_30 > 0:
                needs_improvement.append({"username": u.username, "score": round((1 - acceptance_rate) * failed, 2)})

        hardworking.sort(key=lambda x: x["score"], reverse=True)
        breakthrough.sort(key=lambda x: x["score"], reverse=True)
        needs_improvement.sort(key=lambda x: x["score"], reverse=True)

        return {
            "hardworking": hardworking[:top_n],
            "breakthrough": breakthrough[:top_n],
            "needs_improvement": needs_improvement[:top_n],
        }
