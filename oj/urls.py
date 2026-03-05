# path: oj/urls.py
from django.contrib import admin
from django.urls import path, include
from . import views
from problems import views_admin
from django.views.generic import RedirectView
from submissions import views_callback

from oj import views as roadmap_views
from . import views_api
urlpatterns = [
    # ==========================
    # 🌐 Trang chủ
    # ==========================
    path("", views.home, name="home"),

    # ==========================
    # 📘 Roadmap & Chủ đề học
    # ==========================
#    path("roadmap/detail/", RedirectView.as_view(url="/", permanent=False)),
#    path("roadmap/", RedirectView.as_view(url="/", permanent=False)),
#    path("stages/<int:stage_id>/", views.roadmap_stage),
#    path("stages/<int:stage_id>/topic/<int:topic_index>/", views.topic_detail),
#    path("roadmap/stage/<int:stage_id>/", views.roadmap_stage, name="roadmap_stage"),
#    path("roadmap/stage/<int:stage_id>/topic/<int:topic_index>/", views.topic_detail, name="topic_detail"),
#    path("roadmap/run/", views.run_code_for_roadmap, name="run_code_for_roadmap"),
#    path("roadmap/stage/<int:stage_id>/topic/<int:topic_id>/", views.topic_detail, name="topic_detail"),

    path("roadmap/detail/", RedirectView.as_view(url="/", permanent=False)),
    path("roadmap/", RedirectView.as_view(url="/", permanent=False)),

    # Giai đoạn (stage)
    path("roadmap/stage/<int:stage_id>/", roadmap_views.roadmap_stage, name="roadmap_stage"),

    # Chủ đề (topic) trong giai đoạn
    path("roadmap/stage/<int:stage_id>/topic/<int:topic_index>/",
         roadmap_views.topic_detail, name="topic_detail"),

    # Trình chạy code thử nghiệm
    path("roadmap/run/", roadmap_views.run_code_for_roadmap, name="run_code_for_roadmap"),

    path("roadmap/api/check_login/", views_api.check_login, name="check_login"), 


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
    path("admin/problems/ai_analyze_problem/", views_admin.ai_analyze_problem, name="ai_analyze_problem"),

    # ==========================
    # 👤 Tài khoản & Xác thực
    # ==========================
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("accounts/", include("allauth.urls")),

    # ==========================
    # 💻 Ứng dụng chính
    # ==========================
    path("problems/", include(("problems.urls", "problems"), namespace="problems")),
    path("submissions/", include(("submissions.urls", "submissions"), namespace="submissions")),
    path("contests/", include(("contests.urls", "contests"), namespace="contests")),
    path("api/judge/callback/", views_callback.judge_callback, name="judge_callback_api"),
    
    # ==========================
    # 💻 Ảena
    # ==========================    
    
    
    path("arena/", include("arena.urls", namespace="arena")),

]
