from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    # 🌐 Trang chủ
    path("", views.home, name="home"),

    # ⚙️ Admin
    path("admin/", admin.site.urls),

    # 👤 Tài khoản & Allauth
    path("accounts/", include("allauth.urls")),  # Thêm dòng này ✅
    path("accounts/", include("accounts.urls")),  # App riêng nếu có view custom

    # 🧩 Các module chính
    path("problems/", include("problems.urls")),
    path("submissions/", include("submissions.urls")),
    path("contests/", include("contests.urls")),

    # 🌈 Lộ trình học
    path("roadmap/stage/<int:stage_id>/", views.roadmap_stage, name="roadmap_stage"),
    path("roadmap/run/", views.run_code_online, name="run_code_online"),
    path("stages/<int:stage_id>/topic/<int:topic_index>/", views.topic_detail, name="topic_detail"),
]
