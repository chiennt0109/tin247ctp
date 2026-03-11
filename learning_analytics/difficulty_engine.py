from submissions.models import Submission


class DifficultyEngine:
    @staticmethod
    def level_from_rating(rating: int) -> str:
        if rating < 1200:
            return "Beginner"
        if rating < 1600:
            return "Easy"
        if rating < 2000:
            return "Medium"
        if rating < 2400:
            return "Hard"
        return "Expert"

    def estimate_problem_rating(self, problem):
        total = problem.submission_count or Submission.objects.filter(problem=problem).count()
        ac = problem.ac_count or Submission.objects.filter(problem=problem, verdict="Accepted").count()
        ac_rate = (ac / total) if total else 0.0

        attempted_users = Submission.objects.filter(problem=problem).values("user_id").distinct()
        avg_attempts = 1.0
        count_users = attempted_users.count()
        if count_users:
            avg_attempts = Submission.objects.filter(problem=problem).count() / count_users

        rating = int(2000 - (ac_rate * 800) + min((avg_attempts - 1) * 40, 300))
        rating = max(800, min(3200, rating))
        return rating, self.level_from_rating(rating)

    def update_problem(self, problem):
        rating, level = self.estimate_problem_rating(problem)
        changed = problem.difficulty_rating != rating or problem.difficulty_level != level
        if changed:
            problem.difficulty_rating = rating
            problem.difficulty_level = level
            problem.save(update_fields=["difficulty_rating", "difficulty_level"])
        return rating, level
