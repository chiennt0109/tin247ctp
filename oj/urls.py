from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    # 🏠 Trang chủ
    path("", views.home, name="home"),

    # ⚙️ Django Admin
    path("admin/", admin.site.urls),

    # 👤 Xác thực người dùng (đăng ký, đăng nhập, social login)
    path("accounts/", include("allauth.urls")),

    # 🧩 Ứng dụng OJ chính
    path("accounts/", include("accounts.urls")),
    path("problems/", include("problems.urls")),
    path("submissions/", include("submissions.urls")),
    path("contests/", include("contests.urls")),

    # 📘 Lộ trình học / bài học chi tiết
    path("roadmap/stage/<int:stage_id>/", views.roadmap_stage, name="roadmap_stage"),
    path("stages/<int:stage_id>/topic/<int:topic_index>/", views.topic_detail, name="topic_detail"),

    # 💻 Chạy code online (AJAX endpoint)
    path("roadmap/run/", views.run_code_online, name="run_code_online"),
]

# ✅ Chạy local hoặc Render vẫn hiển thị được ảnh / static
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
