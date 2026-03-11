from collections import defaultdict

from .analytics_engine import AnalyticsEngine
from .recommendation_engine import RecommendationEngine


class AICoach:
    def __init__(self):
        self.analytics = AnalyticsEngine()
        self.recommendation = RecommendationEngine()

    def weak_skills(self, user, limit=5):
        return self.analytics.compute_weak_skills(user, limit=limit)

    def daily_training_plan(self, user):
        weak = self.weak_skills(user, limit=3)
        recs = self.recommendation.recommend_problems(user, limit=12)
        grouped = defaultdict(list)
        for rec in recs:
            if len(grouped[rec["skill"]]) < 2:
                grouped[rec["skill"]].append(rec["problem"].code)

        tasks = []
        for item in weak:
            sname = item["skill"].name
            tasks.append({"skill": sname, "problems": grouped.get(sname, [])[:2]})

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
