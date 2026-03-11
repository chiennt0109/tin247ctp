from django.contrib.auth.models import User
from django.core.cache import cache

from .ai_coach import AICoach
from .analytics_engine import AnalyticsEngine
from .prediction_engine import PredictionEngine
from .recommendation_engine import RecommendationEngine
from .skill_engine import SkillEngine


def update_student_analytics(user_id=None):
    users = User.objects.filter(id=user_id) if user_id else User.objects.filter(is_staff=False)
    skill_engine = SkillEngine()
    analytics = AnalyticsEngine()
    predictor = PredictionEngine()
    recommender = RecommendationEngine()

    for user in users:
        skill_engine.update_user_skill_scores(user)
        payload = {
            "analytics": analytics.contest_analysis(user),
            "weakness": analytics.compute_weak_skills(user),
            "prediction": predictor.predict_student_level(user),
            "recommendations": recommender.recommend_problems(user),
        }
        cache.set(f"learning_analytics:{user.id}", payload, timeout=6 * 3600)


def update_student_training_plan(user_id=None):
    users = User.objects.filter(id=user_id) if user_id else User.objects.filter(is_staff=False)
    coach = AICoach()
    for user in users:
        cache.set(
            f"learning_training_plan:{user.id}",
            {
                "daily": coach.daily_training_plan(user),
                "weekly": coach.weekly_training_plan(user),
            },
            timeout=6 * 3600,
        )


def enqueue_update_student_analytics():
    import django_rq

    scheduler = django_rq.get_scheduler("default")
    scheduler.schedule(scheduled_time=None, func=update_student_analytics, interval=6 * 3600, repeat=None)
    scheduler.schedule(scheduled_time=None, func=update_student_training_plan, interval=6 * 3600, repeat=None)
