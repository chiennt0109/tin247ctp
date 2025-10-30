# path: oj/urls.py
from django.contrib import admin
from django.urls import path, include
from . import views
from problems import views_admin

urlpatterns = [
    path("", views.home, name="home"),

    # Roadmap
    path("stage/<int:stage_id>/", views.roadmap_stage, name="roadmap_stage"),
    path("stage/<int:stage_id>/topic/<int:topic_index>/", views.topic_detail, name="topic_detail"),

    # ✅ Run code UI (page)
    path("run_code/", views.run_code_page, name="run_code_page"),

    # ✅ Run code API (JSON)
    path("api/run_code/", views.run_code_online, name="run_code_online"),

    # Admin
    path("admin/", admin.site.urls),

    # Problems
    path("problems/", include("problems.urls")),

    # ✅ Submissions system
    path("submissions/", include("submissions.urls")),

    # Admin AI
    path("admin/problems/ai_analyze_problem/", views_admin.ai_analyze_problem, name="ai_analyze_problem"),
]
