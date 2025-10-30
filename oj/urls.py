# path: oj/urls.py
from django.contrib import admin
from django.urls import path, include
from . import views
from problems import views_admin

urlpatterns = [
    # 🏠 Trang chủ
    path("", views.home, name="home"),

    # 📚 Lộ trình học / Roadmap
    path("roadmap/stage/<int:stage_id>/", views.roadmap_stage, name="roadmap_stage"),
    path("roadmap/stage/<int:stage_id>/topic/<int:topic_index>/", views.topic_detail, name="topic_detail"),

    # ▶️ API chạy code trên trang roadmap
    path("roadmap/run/", views.run_code_for_roadmap, name="run_code_for_roadmap"),

    # 💻 Chạy code demo (trang riêng)
    path("run_code/", views.run_code_online, name="run_code_online"),
    path("run_code/page/", views.run_code_page, name="run_code_page"),
    path("api/run_code/", views.api_run_code, name="api_run_code"),

    # ⚙️ Khu vực quản trị
    path("admin/", admin.site.urls),

    # 📝 Hệ thống bài tập
    path("problems/", include("problems.urls")),

    # 🚀 Hệ thống nộp bài
    path("submissions/", include("submissions.urls")),

    # 🤖 API AI dành riêng cho Admin
    path("admin/problems/ai_analyze_problem/", views_admin.ai_analyze_problem, name="ai_analyze_problem"),
]
