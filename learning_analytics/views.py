from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.db.models import Avg, Count
from django.shortcuts import render

from submissions.models import Submission

from .analytics_engine import AnalyticsEngine


@staff_member_required
def admin_learning_dashboard(request):
    return render(request, "learning_analytics/admin_dashboard.html")


@staff_member_required
def student_dashboard(request):
    students = User.objects.filter(is_staff=False).annotate(total_submissions=Count("submission"))[:50]
    return render(request, "learning_analytics/student_analytics.html", {"students": students})


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
