from django.urls import path

from assessment import views


app_name = "assessment"

urlpatterns = [
    path("", views.exam_list_redirect, name="home"),
    path("exams/", views.exam_list, name="exam_list"),
    path("exams/<slug:slug>/start/", views.start_exam, name="start_exam"),
    path("attempts/<uuid:attempt_id>/debug/", views.attempt_debug, name="attempt_debug"),
]
