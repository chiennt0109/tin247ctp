# path: oj/urls.py
from django.contrib import admin
from django.urls import path, include

# Nếu bạn có views riêng cho trang chủ thì giữ lại:
from . import views

# ✅ Import đúng cách: views_admin nằm trong app "problems"
from problems import views_admin

urlpatterns = [
    # Trang quản trị Django
    path("admin/", admin.site.urls),

    # Trang người dùng chính
    path("", views.home, name="home"),  # nếu có view home, hoặc có thể bỏ

    # Toàn bộ hệ thống bài toán và AI liên quan
    path("problems/", include("problems.urls")),

    # ✅ Cho phép admin gọi trực tiếp API AI phân tích
    path("problems/ai_analyze_problem/", views_admin.ai_analyze_problem, name="ai_analyze_problem"),
]
