from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.admin.views.decorators import staff_member_required

from .ai_coach import AICoach
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
from .profile_service import LearningProfileService
from .models import UserSkillStats
from .skill_detector import detect_and_assign
from .coverage_analyzer import SkillCoverageAnalyzer
from .roadmap_builder import RoadmapBuilder
from .leaderboard_service import LearningLeaderboardService
from problems.models import Problem


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
    user = User.objects.get(pk=id)
    radar = AnalyticsEngine().radar_chart(user)
    details = [serialize_user_skill(s) for s in UserSkill.objects.filter(user_id=id).select_related("skill")]
    return JsonResponse({"radar": radar, "details": details})


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


@require_GET
def student_training_plan(request, id):
    user = User.objects.get(pk=id)
    coach = AICoach()
    payload = coach.training_plan(user)
    # backward compatibility for existing UI
    payload["daily"] = payload.get("daily_training", {})
    payload["weekly"] = payload.get("weekly_training", {})
    return JsonResponse(payload)


@require_GET
def student_weak_skills(request, id):
    user = User.objects.get(pk=id)
    coach = AICoach()
    weak = coach.weak_skills(user)
    return JsonResponse({"weak_skills": [{"skill": x["skill"].name, "weakness": x["weakness_score"]} for x in weak]})


@staff_member_required
@require_GET
def admin_user_learning_profile(request, id):
    profile = LearningProfileService().build_profile(id)
    return JsonResponse(profile)


@staff_member_required
@require_GET
def skill_detection(request):
    created = 0
    detected_items = []
    for problem in Problem.objects.prefetch_related("tags").all():
        detected, cnt = detect_and_assign(problem)
        created += cnt
        if detected:
            detected_items.append({"problem": problem.code, "skills": [s.name for s in detected]})
    return JsonResponse({"created_links": created, "detected": detected_items[:200]})


@staff_member_required
@require_GET
def skill_coverage(request):
    data = SkillCoverageAnalyzer().analyze()
    return JsonResponse(data)


@require_GET
def roadmap_track(request, track):
    data = RoadmapBuilder().get_track(track)
    if not data:
        return JsonResponse({"error": "track not found"}, status=404)
    return JsonResponse(data)


@require_GET
def learning_leaderboard(request):
    data = LearningLeaderboardService().compute(top_n=3)
    return JsonResponse(data)


@require_GET
def student_skill_mastery(request, id):
    user = User.objects.get(pk=id)
    stats = UserSkillStats.objects.filter(user=user).select_related("skill").order_by("mastery_score")
    data = []
    for st in stats:
        if st.mastery_score < 30:
            level = "Beginner"
        elif st.mastery_score < 60:
            level = "Intermediate"
        elif st.mastery_score < 85:
            level = "Advanced"
        else:
            level = "Expert"
        data.append({
            "skill": st.skill.name,
            "mastery_score": st.mastery_score,
            "level": level,
            "problems_solved": st.solved_problems,
            "attempts": st.attempts,
            "successes": st.successes,
        })
    return JsonResponse({"skill_mastery": data})
