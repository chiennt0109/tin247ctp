# path: oj/urls.py
from django.contrib import admin
from django.urls import path, include
from . import views

# 🧩 Import thêm để chạy migrate tạm
from django.http import HttpResponse
from django.core.management import call_command

def run_migrate(request):
    call_command("makemigrations", "problems")
    call_command("makemigrations", "submissions")
    call_command("migrate")
    return HttpResponse("✅ Migration executed successfully!")

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

    # ⚙️ Endpoint tạm thời để migrate thủ công
    path("run-migrate/", run_migrate),
]
