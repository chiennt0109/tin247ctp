from django.urls import path
from . import views

urlpatterns = [
    path("", views.problem_list, name="problems"),
    path("submissions/", views.submission_list, name="subs"),
]
