from collections import defaultdict

from .analytics_engine import AnalyticsEngine
from .models import ProblemSkill, UserSkillStats
from .recommendation_engine import RecommendationEngine
from .skill_engine import SkillEngine


class AICoach:
    def __init__(self):
        self.analytics = AnalyticsEngine()
        self.recommendation = RecommendationEngine()
        self.skill_engine = SkillEngine()

    def weak_skills(self, user, limit=5):
        return self.analytics.compute_weak_skills(user, limit=limit)

    def _difficulty_for_mastery(self, mastery):
        if mastery < 30:
            return "Easy"
        if mastery < 60:
            return "Medium"
        return "Hard"

    def recommended_skills(self, user, limit=5):
        stats = (
            UserSkillStats.objects.filter(user=user)
            .select_related("skill")
            .order_by("mastery_score")[:limit]
        )
        return [
            {
                "skill": st.skill.name,
                "mastery_score": st.mastery_score,
                "target_difficulty": self._difficulty_for_mastery(st.mastery_score),
                "level": self.skill_engine.mastery_level(st.mastery_score),
            }
            for st in stats
        ]

    def daily_training_plan(self, user):
        weak = self.recommended_skills(user, limit=3)
        tasks = []
        for item in weak:
            links = (
                ProblemSkill.objects.filter(skill__name=item["skill"], problem__difficulty=item["target_difficulty"])
                .select_related("problem")[:2]
            )
            tasks.append({"skill": item["skill"], "problems": [x.problem.code for x in links]})

        return {
            "title": "Today Training Plan",
            "tasks": tasks,
            "contest_practice": 1,
        }

    def weekly_training_plan(self, user):
        ordered = self.recommendation.personalized_learning_path(user)[:5]
        return {
            "title": "Week Plan",
            "days": [{"day": idx + 1, "focus": skill.name} for idx, skill in enumerate(ordered)],
        }

    def training_plan(self, user):
        return {
            "daily_training": self.daily_training_plan(user),
            "weekly_training": self.weekly_training_plan(user),
            "recommended_skills": self.recommended_skills(user, limit=6),
        }
