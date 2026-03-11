from django.contrib.auth.models import User
from django.core.cache import cache

from problems.models import Problem

from .ai_coach import AICoach
from .analytics_engine import AnalyticsEngine
from .coverage_analyzer import SkillCoverageAnalyzer
from .difficulty_engine import DifficultyEngine
from .leaderboard_service import LearningLeaderboardService
from .prediction_engine import PredictionEngine
from .profile_service import LearningProfileService
from .recommendation_engine import RecommendationEngine
from .roadmap_builder import RoadmapBuilder
from .skill_detector import detect_and_assign
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
        cache.set(f"learning_training_plan:{user.id}", coach.training_plan(user), timeout=6 * 3600)


def update_user_learning_profile_cache(user_id=None):
    users = User.objects.filter(id=user_id) if user_id else User.objects.filter(is_staff=False)
    service = LearningProfileService()
    for user in users:
        service.build_profile(user.id, force=True)


def update_skill_detection():
    for problem in Problem.objects.prefetch_related("tags").all():
        detect_and_assign(problem)


def update_skill_mastery(user_id=None):
    users = User.objects.filter(id=user_id) if user_id else User.objects.filter(is_staff=False)
    skill_engine = SkillEngine()
    for user in users:
        skill_engine.update_user_skill_scores(user)


def update_problem_difficulty(problem_id=None):
    problems = Problem.objects.filter(id=problem_id) if problem_id else Problem.objects.all()
    engine = DifficultyEngine()
    for problem in problems:
        engine.update_problem(problem)


def update_skill_coverage():
    coverage = SkillCoverageAnalyzer().analyze()
    cache.set("skill_coverage_cache", coverage, timeout=6 * 3600)


def build_training_tracks():
    built = RoadmapBuilder().build_all()
    cache.set("training_tracks_cache", built, timeout=6 * 3600)


def update_recommendations(user_id=None):
    users = User.objects.filter(id=user_id) if user_id else User.objects.filter(is_staff=False)
    recommender = RecommendationEngine()
    for user in users:
        cache.set(f"recommended_problems:{user.id}", recommender.recommend_problems(user, limit=10), timeout=6 * 3600)


def update_learning_leaderboard():
    board = LearningLeaderboardService().compute(top_n=10)
    cache.set("learning_leaderboard_cache", board, timeout=6 * 3600)


def enqueue_update_student_analytics():
    import django_rq

    scheduler = django_rq.get_scheduler("default")
    scheduler.schedule(scheduled_time=None, func=update_student_analytics, interval=6 * 3600, repeat=None)
    scheduler.schedule(scheduled_time=None, func=update_student_training_plan, interval=6 * 3600, repeat=None)
    scheduler.schedule(scheduled_time=None, func=update_user_learning_profile_cache, interval=6 * 3600, repeat=None)
    scheduler.schedule(scheduled_time=None, func=update_skill_detection, interval=6 * 3600, repeat=None)
    scheduler.schedule(scheduled_time=None, func=update_skill_mastery, interval=6 * 3600, repeat=None)
    scheduler.schedule(scheduled_time=None, func=update_problem_difficulty, interval=6 * 3600, repeat=None)
    scheduler.schedule(scheduled_time=None, func=update_skill_coverage, interval=6 * 3600, repeat=None)
    scheduler.schedule(scheduled_time=None, func=build_training_tracks, interval=6 * 3600, repeat=None)
    scheduler.schedule(scheduled_time=None, func=update_recommendations, interval=6 * 3600, repeat=None)
    scheduler.schedule(scheduled_time=None, func=update_learning_leaderboard, interval=6 * 3600, repeat=None)
