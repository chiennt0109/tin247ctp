# path: problems/urls.py
from django.urls import path
from . import views, views_admin, views_profile

app_name = "problems"

urlpatterns = [
    # ======================
    # 🧩 Bài toán
    # ======================
    path("", views.problem_list, name="problem_list"),
    path("<int:pk>/", views.problem_detail, name="problem_detail"),

    # ======================
    # 👤 Hồ sơ & tài khoản học tập
    # ======================
    path("profile/", views_profile.profile_view, name="profile"),
    path("change-password/", views_profile.change_password_view, name="change_password"),

    # ======================
    # 🤖 AI Features
    # ======================
    path("<int:pk>/ai_hint/", views.ai_hint, name="ai_hint"),
    path("<int:pk>/ai_debug/", views.ai_debug, name="ai_debug"),
    path("<int:pk>/ai_recommend/", views.ai_recommend, name="ai_recommend"),
    path("<int:pk>/ai_solution/", views.get_solution, name="ai_solution"),
    path("<int:pk>/ai_next/", views.get_next_recommendation, name="ai_next"),

    # Học tập & gợi ý cá nhân
    path("ai_learning_path/", views.ai_learning_path, name="ai_learning_path"),
    path("ai_recommend_personal/", views.ai_recommend_personal, name="ai_recommend_personal"),

    # ======================
    # 🧠 AI Tools cho Admin
    # ======================
    #path("ai_suggest_tags/", views_admin.ai_suggest_tags, name="ai_suggest_tags"),
    path("ai_analyze_problem/", views_admin.ai_analyze_problem, name="ai_analyze_problem"),
    path("admin_ai_generate/", views.admin_ai_generate),
    path("admin_ai_samples/", views.admin_ai_samples),
    path("admin_ai_check/", views.admin_ai_check),
    path("<int:pk>/buy-editorial/", views.buy_editorial, name="buy_editorial"),

]
