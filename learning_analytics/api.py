from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .analytics_engine import AnalyticsEngine
from .prediction_engine import PredictionEngine
from .recommendation_engine import RecommendationEngine
from .serializers import (
    serialize_learning_path,
    serialize_problem_recommendation,
    serialize_user_skill,
)
from .skill_engine import SkillEngine
from .models import UserSkill


@require_GET
def student_analytics(request, id):
    user = User.objects.get(pk=id)
    skill_engine = SkillEngine()
    skill_engine.update_user_skill_scores(user)

    analytics = AnalyticsEngine()
    prediction = PredictionEngine()
    recommendation = RecommendationEngine()

    payload = {
        "student": user.username,
        "predicted_level": prediction.predict_student_level(user),
        "weak_skills": [
            {"skill": w["skill"].name, "weakness_score": w["weakness_score"]}
            for w in analytics.compute_weak_skills(user)
        ],
        "contest": analytics.contest_analysis(user),
        "error_profile": analytics.submission_error_profile(user),
        "radar": analytics.radar_chart(user),
        "talent": analytics.talent_detector(user),
        "ai_training": recommendation.ai_training_plan(user),
    }
    return JsonResponse(payload)


@require_GET
def student_skills(request, id):
    data = [serialize_user_skill(s) for s in UserSkill.objects.filter(user_id=id).select_related("skill")]
    return JsonResponse({"skills": data})


@require_GET
def student_weakness(request, id):
    user = User.objects.get(pk=id)
    analytics = AnalyticsEngine()
    data = analytics.compute_weak_skills(user)
    return JsonResponse(
        {"weakness": [{"skill": x["skill"].name, "weakness_score": x["weakness_score"]} for x in data]}
    )


@require_GET
def student_recommendations(request, id):
    user = User.objects.get(pk=id)
    engine = RecommendationEngine()
    data = [serialize_problem_recommendation(r) for r in engine.recommend_problems(user)]
    return JsonResponse({"recommendations": data})


@require_GET
def student_learning_path(request, id):
    user = User.objects.get(pk=id)
    engine = RecommendationEngine()
    data = [serialize_learning_path(s, idx + 1) for idx, s in enumerate(engine.personalized_learning_path(user))]
    return JsonResponse({"learning_path": data})


@require_GET
def student_contest_analysis(request, id):
    user = User.objects.get(pk=id)
    data = AnalyticsEngine().contest_analysis(user)
    return JsonResponse(data)
