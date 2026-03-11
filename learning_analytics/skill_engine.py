from django.utils import timezone

from submissions.models import Submission

from .models import ProblemSkill, UserSkill, UserSkillStats, UserTopicStats

DIFFICULTY_WEIGHTS = {"Easy": 0.3, "Medium": 0.6, "Hard": 1.0}


class SkillEngine:
    @staticmethod
    def classify_level(score: float) -> str:
        if score < 0.3:
            return UserSkill.LEVEL_WEAK
        if score < 0.6:
            return UserSkill.LEVEL_BASIC
        if score < 0.8:
            return UserSkill.LEVEL_INTERMEDIATE
        return UserSkill.LEVEL_STRONG

    def update_user_skill_scores(self, user):
        now = timezone.now()
        skills = set(ProblemSkill.objects.values_list("skill_id", flat=True))
        for skill_id in skills:
            problem_links = list(ProblemSkill.objects.filter(skill_id=skill_id).select_related("problem"))
            problem_ids = [link.problem_id for link in problem_links]
            total_skill_problems = len(problem_ids)
            if total_skill_problems == 0:
                continue

            user_subs = Submission.objects.filter(user=user, problem_id__in=problem_ids)
            attempted = user_subs.values("problem_id").distinct().count()
            solved_ids = set(
                user_subs.filter(verdict="Accepted").values_list("problem_id", flat=True).distinct()
            )
            solved = len(solved_ids)

            solve_rate = solved / attempted if attempted else 0.0
            attempt_rate = attempted / total_skill_problems
            solved_links = [link for link in problem_links if link.problem_id in solved_ids]
            difficulty_weight = (
                sum(DIFFICULTY_WEIGHTS.get(link.problem.difficulty, 0.3) for link in solved_links) / len(solved_links)
                if solved_links
                else 0.0
            )
            weighted_score = (0.6 * solve_rate) + (0.2 * attempt_rate) + (0.2 * difficulty_weight)
            simple_score = solve_rate
            level = self.classify_level(weighted_score)

            UserSkillStats.objects.update_or_create(
                user=user,
                skill_id=skill_id,
                defaults={
                    "attempted_problems": attempted,
                    "solved_problems": solved,
                    "skill_score": round(simple_score, 4),
                    "updated_at": now,
                },
            )
            UserTopicStats.objects.update_or_create(
                user=user,
                skill_id=skill_id,
                defaults={
                    "attempted": attempted,
                    "solved": solved,
                    "acceptance_rate": solve_rate,
                    "progress": attempt_rate,
                    "last_updated": now,
                },
            )
            UserSkill.objects.update_or_create(
                user=user,
                skill_id=skill_id,
                defaults={
                    "skill_score": round(weighted_score, 4),
                    "level": level,
                    "last_updated": now,
                },
            )
