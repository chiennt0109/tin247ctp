from django.db.models import Avg

from submissions.models import Submission

from .analytics_engine import AnalyticsEngine
from .models import ProblemSkill, UserSkill


class RecommendationEngine:
    def __init__(self):
        self.analytics = AnalyticsEngine()

    def recommend_problems(self, user, limit=10):
        weak_skills = self.analytics.compute_weak_skills(user)
        solved_ids = set(
            Submission.objects.filter(user=user, verdict="Accepted")
            .values_list("problem_id", flat=True)
            .distinct()
        )
        user_level = (
            UserSkill.objects.filter(user=user).aggregate(avg=Avg("skill_score")).get("avg") or 0
        )
        target_difficulty = "Easy" if user_level < 0.4 else "Medium" if user_level < 0.7 else "Hard"

        candidates = []
        for idx, weak in enumerate(weak_skills):
            skill_priority = 1 - (idx / max(len(weak_skills), 1))
            links = ProblemSkill.objects.filter(skill=weak["skill"]).select_related("problem")
            for link in links:
                p = link.problem
                if p.id in solved_ids:
                    continue
                difficulty_match = 1.0 if p.difficulty == target_difficulty else 0.5
                popularity = min((p.ac_count + 1) / max(p.submission_count + 1, 1), 1.0)
                score = (0.5 * skill_priority) + (0.3 * difficulty_match) + (0.2 * popularity)
                candidates.append(
                    {
                        "problem": p,
                        "score": round(score, 4),
                        "skill": weak["skill"].name,
                        "difficulty_match": difficulty_match,
                    }
                )

        candidates.sort(key=lambda x: x["score"], reverse=True)
        seen = set()
        dedup = []
        for candidate in candidates:
            if candidate["problem"].id in seen:
                continue
            dedup.append(candidate)
            seen.add(candidate["problem"].id)
            if len(dedup) >= limit:
                break
        return dedup

    def ai_training_plan(self, user):
        weak_skills = self.analytics.compute_weak_skills(user, limit=3)
        recommendations = self.recommend_problems(user, limit=12)
        grouped = {w["skill"].name: [] for w in weak_skills}
        for rec in recommendations:
            if rec["skill"] in grouped and len(grouped[rec["skill"]]) < 2:
                grouped[rec["skill"]].append(rec["problem"].title)
        return grouped

    def personalized_learning_path(self, user):
        weak_skills = [w["skill"] for w in self.analytics.compute_weak_skills(user, limit=10)]
        ordered = []
        seen = set()

        def add_with_prereq(skill):
            prereqs = [p.prerequisite for p in skill.prerequisites.select_related("prerequisite").all()]
            for prereq in prereqs:
                if prereq.id not in seen:
                    add_with_prereq(prereq)
            if skill.id not in seen:
                ordered.append(skill)
                seen.add(skill.id)

        for skill in weak_skills:
            add_with_prereq(skill)
        return ordered
