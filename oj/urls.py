# path: problems/urls.py
from django.urls import path
from . import views, views_admin

urlpatterns = [
    # ==========================
    # 🌐 Trang người dùng
    # ==========================
    path("", views.problem_list, name="problem_list"),
    path("<int:pk>/", views.problem_detail, name="problem_detail"),

    # 🤖 Các API AI hỗ trợ khi làm bài
    path("<int:pk>/ai_hint/", views.ai_hint_real, name="ai_hint"),
    path("<int:pk>/ai_debug/", views.ai_debug, name="ai_debug"),
    path("<int:pk>/ai_recommend/", views.ai_recommend, name="ai_recommend"),

    # 🧭 Lộ trình học
    path("ai_learning_path/", views.ai_learning_path, name="ai_learning_path"),

    # ==========================
    # 🧠 Công cụ AI trong admin
    # ==========================
    # Gợi ý tag đơn giản (rule-based)
    path("ai_suggest_tags/", views_admin.ai_suggest_tags, name="ai_suggest_tags"),

    # Phân tích toàn diện: sinh mã bài, độ khó, tag
    path("ai_analyze_problem/", views_admin.ai_analyze_problem, name="ai_analyze_problem"),
]
