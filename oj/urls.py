# path: oj/urls.py
from django.contrib import admin
from django.urls import path, include
from . import views
from problems import views_admin

urlpatterns = [
    # 🧭 Trang chủ & Roadmap học tập
    path("", views.home, name="home"),
    path("stage/<int:stage_id>/", views.roadmap_stage, name="roadmap_stage"),
    path("stage/<int:stage_id>/topic/<int:topic_index>/", views.topic_detail, name="topic_detail"),

    # 💻 Chạy code trực tuyến
    path("run_code/", views.run_code_online, name="run_code_online"),

    # ⚙️ Khu vực quản trị
    path("admin/", admin.site.urls),

    # 📘 Hệ thống bài tập Problems
    path("problems/", include("problems.urls")),

    # 📤 Hệ thống nộp bài Submissions ✅ thêm dòng này
    path("submissions/", include("submissions.urls")),

    # 🧠 API AI dành riêng cho Admin
    path("admin/problems/ai_analyze_problem/", views_admin.ai_analyze_problem, name="ai_analyze_problem"),
]
