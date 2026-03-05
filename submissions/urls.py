# path: submissions/urls.py
from django.urls import path
from . import views, views_callback, views_api

app_name = "submissions"

urlpatterns = [
    # 🧾 Form nộp bài (GET)
    # /submissions/<problem_id>/
    path("<int:problem_id>/", views.submission_page, name="submission_page"),

    # 🚀 API xử lý nộp bài (POST)
    # /submissions/<problem_id>/submit/
    path("<int:problem_id>/submit/", views.submission_create, name="submission_create"),

    # 📄 Chi tiết bài nộp
    # /submissions/<submission_id>/detail/
    path("<int:submission_id>/detail/", views.submission_detail, name="submission_detail"),

    # 📨 Worker callback
    path("callback/", views_callback.judge_callback, name="judge_callback"),

    # 📊 Kết quả JSON
    # /submissions/<sid>/json/
    path("<int:sid>/json/", views_api.submission_json, name="submission_json"),

    # 🔴 Stream SSE
    # /submissions/<sid>/stream/
    path("<int:sid>/stream/", views_api.submission_stream, name="submission_stream"),
]
