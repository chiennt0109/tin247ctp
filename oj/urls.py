# path: oj/urls.py
from django.contrib import admin
from django.urls import path, include
from . import views
from problems import views_admin
from django.views.generic import RedirectView
from submissions import views_callback

from oj import views as roadmap_views
from . import views_api
from learning_analytics import api as learning_analytics_api
from learning_analytics import views as learning_analytics_views
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

    path("api/student/<int:id>/analytics", learning_analytics_api.student_analytics, name="student_analytics"),
    path("api/student/<int:id>/skills", learning_analytics_api.student_skills, name="student_skills"),
    path("api/student/<int:id>/weakness", learning_analytics_api.student_weakness, name="student_weakness"),
    path("api/student/<int:id>/recommendations", learning_analytics_api.student_recommendations, name="student_recommendations"),
    path("api/student/<int:id>/learning-path", learning_analytics_api.student_learning_path, name="student_learning_path"),
    path("api/student/<int:id>/contest-analysis", learning_analytics_api.student_contest_analysis, name="student_contest_analysis"),
    path("api/student/<int:id>/training_plan", learning_analytics_api.student_training_plan, name="student_training_plan"),
    path("api/student/<int:id>/weak_skills", learning_analytics_api.student_weak_skills, name="student_weak_skills"),
    path("api/admin/user/<int:id>/learning_profile", learning_analytics_api.admin_user_learning_profile, name="admin_user_learning_profile"),
    path("api/skill_detection", learning_analytics_api.skill_detection, name="skill_detection"),
    path("api/skill_coverage", learning_analytics_api.skill_coverage, name="skill_coverage"),
    path("api/roadmap/<slug:track>", learning_analytics_api.roadmap_track, name="roadmap_track"),
    path("api/learning_leaderboard", learning_analytics_api.learning_leaderboard, name="learning_leaderboard"),

    # ==========================
    # 🧩 Quản trị & AI Tools
    # ==========================
    path("admin/", admin.site.urls),
    path("admin/problems/ai_analyze_problem/", views_admin.ai_analyze_problem, name="ai_analyze_problem"),
    path("admin/learning-analytics/", learning_analytics_views.admin_learning_dashboard, name="admin_learning_analytics"),
    path("analytics/user/<int:user_id>/", learning_analytics_views.user_learning_profile, name="analytics_user_learning_profile"),

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
    path("learning-analytics/", include(("learning_analytics.urls", "learning_analytics"), namespace="learning_analytics")),
    path("analytics/", include(("learning_analytics.urls", "learning_analytics"), namespace="learning_analytics_public")),

]
