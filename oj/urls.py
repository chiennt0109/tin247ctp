# path: oj/urls.py
from django.contrib import admin
from django.urls import path, include
from . import views


# path: oj/urls.py
from django.core.management import call_command
from django.http import HttpResponse

def run_migrate_safe(request):
    """Endpoint an toàn để migrate trên Render (không cần input)."""
    try:
        call_command("makemigrations", "problems", interactive=False)
        call_command("migrate", interactive=False)
        return HttpResponse("✅ Migrate thành công (safe mode).")
    except Exception as e:
        return HttpResponse(f"❌ Lỗi migrate: {e}")


urlpatterns = [
    path("", views.home, name="home"),
    path("admin/", admin.site.urls),

    # 🧩 Hệ thống tài khoản
    path("accounts/", include("allauth.urls")),

    # 🧠 Ứng dụng chính
    path("problems/", include("problems.urls")),
    path("submissions/", include("submissions.urls")),
    path("contests/", include("contests.urls")),

    # 🌈 Lộ trình học
    path("roadmap/stage/<int:stage_id>/", views.roadmap_stage, name="roadmap_stage"),
    path("roadmap/run/", views.run_code_online, name="run_code_online"),
    path("stages/<int:stage_id>/topic/<int:topic_index>/", views.topic_detail, name="topic_detail"),

]

urlpatterns += [
    path("run-migrate-safe/", run_migrate_safe, name="run_migrate_safe"),
]
