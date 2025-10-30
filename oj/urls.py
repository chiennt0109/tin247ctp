# path: oj/urls.py
from django.contrib import admin
from django.urls import path, include
from . import views
from problems import views_admin

urlpatterns = [
    # Trang chủ & Roadmap
    path("", views.home, name="home"),
    path("roadmap/stage/<int:stage_id>/", views.roadmap_stage, name="roadmap_stage"),
    path("roadmap/stage/<int:stage_id>/topic/<int:topic_index>/", views.topic_detail, name="topic_detail"),

    # Form chạy code (UI)
    path("run_code/", views.run_code_page, name="run_code_online"),

    # API JSON chạy code (quan trọng)
    path("api/run_code/", views.api_run_code, name="api_run_code"),

    # Admin
    path("admin/", admin.site.urls),

    # Problems
    path("problems/", include("problems.urls")),

    # Submissions
    path("submissions/", include("submissions.urls")),

    # AI admin
    path("admin/problems/ai_analyze_problem/", views_admin.ai_analyze_problem, name="ai_analyze_problem"),
]
