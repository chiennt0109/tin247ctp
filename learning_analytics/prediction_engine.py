from django.db.models import Avg

from submissions.models import Submission


class PredictionEngine:
    def predict_student_level(self, user):
        subs = Submission.objects.filter(user=user)
        attempted = subs.values("problem_id").distinct().count()
        solved = subs.filter(verdict="Accepted").values("problem_id").distinct().count()
        hard_solved = (
            subs.filter(verdict="Accepted", problem__difficulty="Hard").values("problem_id").distinct().count()
        )
        accuracy = solved / attempted if attempted else 0
        speed = 1 - min((subs.aggregate(v=Avg("exec_time")).get("v") or 2) / 4, 1)

        score = (0.5 * accuracy) + (0.3 * min(hard_solved / 30, 1)) + (0.2 * speed)
        if score >= 0.8:
            level = "advanced"
        elif score >= 0.55:
            level = "intermediate"
        else:
            level = "beginner"
        return {"predicted_level": level, "confidence": round(score, 4)}
