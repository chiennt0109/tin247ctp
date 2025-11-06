# path: oj/urls.py
from django.contrib import admin
from django.urls import path, include
from . import views
from problems import views_admin

urlpatterns = [
    # ==========================
    # 🌐 Trang chủ
    # ==========================
    path("", views.home, name="home"),

    # ==========================
    # 📘 Roadmap & chủ đề học
    # ==========================
    # URL cũ (tương thích ngược)
    path("stages/<int:stage_id>/", views.roadmap_stage),
    path("stages/<int:stage_id>/topic/<int:topic_index>/", views.topic_detail),

    # URL mới có tên rõ ràng
    path("roadmap/stage/<int:stage_id>/", views.roadmap_stage, name="roadmap_stage"),
    path(
        "roadmap/stage/<int:stage_id>/topic/<int:topic_index>/",
        views.topic_detail,
        name="topic_detail",
    ),

    # ✅ Run code trong roadmap
    path("roadmap/run/", views.run_code_for_roadmap, name="run_code_for_roadmap"),

    # ==========================
    # ⚙️ Demo Run Code Online
    # ==========================
    path("run_code/", views.run_code_online, name="run_code_online"),
    path("run_code/page/", views.run_code_page, name="run_code_page"),
    path("api/run_code/", views.api_run_code, name="api_run_code"),

    # ==========================
    # 🧩 Quản trị & AI Tools
    # ==========================
    path("admin/", admin.site.urls),
    path(
        "admin/problems/ai_analyze_problem/",
        views_admin.ai_analyze_problem,
        name="ai_analyze_problem",
    ),

    # ==========================
    # 👤 Tài khoản / Xác thực
    # ==========================
    path("accounts/", include("allauth.urls")),

    # ==========================
    # 💻 Ứng dụng chính
    # ==========================
    # Mỗi app chỉ include một lần, có namespace để gọi {% url 'app:view' %}
    path(
        "problems/",
        include(("problems.urls", "problems"), namespace="problems"),
    ),
    path(
        "submissions/",
        include(("submissions.urls", "submissions"), namespace="submissions"),
    ),
    path(
        "contests/",
        include(("contests.urls", "contests"), namespace="contests"),
    ),
]
