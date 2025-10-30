# path: oj/urls.py
from django.contrib import admin
from django.urls import path, include
from . import views
from problems import views_admin

urlpatterns = [
    # 🏠 Trang chủ
    path("", views.home, name="home"),

    # ✅ Roadmap mới
    path("roadmap/stage/<int:stage_id>/", views.roadmap_stage, name="roadmap_stage"),
    path("roadmap/stage/<int:stage_id>/topic/<int:topic_index>/", views.topic_detail, name="topic_detail"),

    # ✅ Hỗ trợ URL cũ (Backward Compatible)
    path("stages/<int:stage_id>/", views.roadmap_stage),
    path("stages/<int:stage_id>/topic/<int:topic_index>/", views.topic_detail),

    # 💻 Chạy code online
    path("run_code/", views.run_code_online, name="run_code_online"),

    # 🧑‍💼 Admin
    path("admin/", admin.site.urls),

    # 📘 Bài tập
    path("problems/", include("problems.urls")),

    # 📨 Nộp bài
    path("submissions/", include("submissions.urls")),

    # 🤖 AI cho Admin
    path("admin/problems/ai_analyze_problem/", views_admin.ai_analyze_problem, name="ai_analyze_problem"),
]
