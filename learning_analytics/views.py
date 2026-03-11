from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render

from submissions.models import Submission

from .analytics_engine import AnalyticsEngine
from .profile_service import LearningProfileService
from .coverage_analyzer import SkillCoverageAnalyzer
from .roadmap_builder import RoadmapBuilder


@staff_member_required
def admin_learning_dashboard(request):
    return render(request, "learning_analytics/admin_dashboard.html")


@staff_member_required
def student_dashboard(request):
    query = request.GET.get("q", "").strip()
    min_rating = request.GET.get("min_rating", "").strip()

    students = User.objects.filter(is_staff=False).annotate(total_submissions=Count("submission"))
    if query:
        students = students.filter(username__icontains=query)

    items = []
    service = LearningProfileService()
    for student in students.order_by("username")[:100]:
        profile = service.build_profile(student.id)
        rating = profile["overview"]["current_rating"]
        if min_rating:
            try:
                if rating < float(min_rating):
                    continue
            except ValueError:
                pass
        items.append({
            "id": student.id,
            "username": student.username,
            "total_submissions": student.total_submissions,
            "rating": rating,
        })

    return render(
        request,
        "learning_analytics/student_analytics.html",
        {"students": items, "q": query, "min_rating": min_rating},
    )


@staff_member_required
def user_learning_profile(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    profile = LearningProfileService().build_profile(user.id)
    return render(
        request,
        "learning_analytics/user_learning_profile.html",
        {"student": user, "profile": profile},
    )


@staff_member_required
def redirect_admin_user_to_learning_profile(request, user_id):
    return redirect("learning_analytics:user_learning_profile", user_id=user_id)


@staff_member_required
def class_dashboard(request):
    analytics = {
        "top_students": User.objects.filter(is_staff=False)
        .annotate(total_submissions=Count("submission"))
        .order_by("-total_submissions")[:10],
        "difficulty_stats": Submission.objects.values("problem__difficulty").annotate(cnt=Count("id")),
    }
    return render(request, "learning_analytics/class_analytics.html", {"analytics": analytics})


@staff_member_required
def contest_dashboard(request):
    contest_data = AnalyticsEngine().contest_analysis(request.user)
    return render(request, "learning_analytics/contest_analytics.html", {"contest_data": contest_data})


@staff_member_required
def topic_dashboard(request):
    topic_heatmap = (
        Submission.objects.values("problem__tags__name")
        .annotate(avg_time=Avg("exec_time"), total=Count("id"))
        .order_by("-total")[:30]
    )
    return render(request, "learning_analytics/topic_analytics.html", {"topic_heatmap": topic_heatmap})


@staff_member_required
def skill_coverage_page(request):
    data = SkillCoverageAnalyzer().analyze()
    return render(request, "learning_analytics/skill_coverage.html", {"coverage": data})


@staff_member_required
def training_tracks_page(request):
    builder = RoadmapBuilder()
    if request.GET.get("rebuild") == "1":
        builder.build_all()
    tracks = []
    for slug in ["graph", "dynamic-programming", "math", "data-structures", "string-algorithms"]:
        track = builder.get_track(slug)
        if track:
            tracks.append(track)
    return render(request, "learning_analytics/training_tracks.html", {"tracks": tracks})
