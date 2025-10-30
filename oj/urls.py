# path: oj/urls.py
from django.contrib import admin
from django.urls import path, include
from . import views
from problems import views_admin

urlpatterns = [
    # 🏠 Trang chủ & Roadmap
    path("", views.home, name="home"),
    path("stage/<int:stage_id>/", views.roadmap_stage, name="roadmap_stage"),
    path("stage/<int:stage_id>/topic/<int:topic_index>/", views.topic_detail, name="topic_detail"),

    # ✅ API chạy code cho giao diện Roadmap
    path("roadmap/run/", views.run_code_for_roadmap, name="run_code_for_roadmap"),

    # 💻 Chạy code online độc lập
    path("run_code/", views.run_code_online, name="run_code_online"),

    # ⚙️ Admin
    path("admin/", admin.site.urls),

    # 📚 Problems
    path("problems/", include("problems.urls")),

    # ✅ Submissions (hệ thống chấm bài)
    path("submissions/", include("submissions.urls")),

    # 🤖 AI Admin
    path("admin/problems/ai_analyze_problem/", views_admin.ai_analyze_problem, name="ai_analyze_problem"),
]
