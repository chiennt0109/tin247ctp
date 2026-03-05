# contests/urls.py
from django.urls import path
from . import views

app_name = "contests"

urlpatterns = [
    path("", views.contest_list, name="contest_list"),
    path("<int:contest_id>/", views.contest_detail, name="contest_detail"),
    path("<int:contest_id>/rank/", views.contest_rank, name="contest_rank"),
    path("<int:contest_id>/rank_json/", views.contest_rank_json, name="contest_rank_json"),

    # ?? PRACTICE MODE
    path("<int:contest_id>/practice/", views.contest_practice, name="contest_practice"),
    path("<int:contest_id>/practice/rank/", views.practice_rank, name="practice_rank"),

]
