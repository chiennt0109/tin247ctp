# path: oj/urls.py
from django.contrib import admin
from django.urls import path, include
from . import views
from problems import views_admin

urlpatterns = [
    path("", views.home, name="home"),

    # ✅ Backward-compatible: URL cũ vẫn chạy
    path("stages/<int:stage_id>/", views.roadmap_stage),
    path("stages/<int:stage_id>/topic/<int:topic_index>/", views.topic_detail),

    # ✅ URL mới
    path("roadmap/stage/<int:stage_id>/", views.roadmap_stage, name="roadmap_stage"),
    path("roadmap/stage/<int:stage_id>/topic/<int:topic_index>/", views.topic_detail, name="topic_detail"),

    # ✅ Run code cho roadmap
    path("roadmap/run/", views.run_code_for_roadmap, name="run_code_for_roadmap"),

    # Demo run code
    path("run_code/", views.run_code_online, name="run_code_online"),
    path("run_code/page/", views.run_code_page, name="run_code_page"),
    path("api/run_code/", views.api_run_code, name="api_run_code"),

    path("admin/", admin.site.urls),
    path("problems/", include("problems.urls")),
    path("submissions/", include("submissions.urls")),
    path("admin/problems/ai_analyze_problem/", views_admin.ai_analyze_problem, name="ai_analyze_problem"),
]
