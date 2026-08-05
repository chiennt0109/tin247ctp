from django.urls import path

from assessment import views


app_name = "assessment"

urlpatterns = [
    path("", views.exam_list_redirect, name="home"),
    path("exams/", views.exam_list, name="exam_list"),
    path("exams/<slug:slug>/start/", views.start_exam, name="start_exam"),
    path("exams/<slug:slug>/resources/create/", views.create_download_resource, name="create_download_resource"),
    path("resources/", views.my_resources, name="my_resources"),
    path(
        "resources/<uuid:package_id>/download/<str:package>/",
        views.download_resource_package, name="resource_download",
    ),
    path("results/", views.result_list, name="result_list"),
    path("results/<uuid:attempt_id>/", views.attempt_result, name="result_detail"),
    path("attempts/<uuid:attempt_id>/", views.attempt_detail, name="attempt_detail"),
    path("attempts/<uuid:attempt_id>/result/", views.attempt_result, name="attempt_result"),
    path(
        "attempts/<uuid:attempt_id>/download/<str:package>/",
        views.download_attempt_package, name="attempt_download",
    ),
    path("api/attempts/<uuid:attempt_id>/answers/", views.autosave_answers, name="autosave_answers"),
    path("api/attempts/<uuid:attempt_id>/submit/", views.submit_attempt_view, name="submit_attempt"),
    path("api/attempts/<uuid:attempt_id>/state/", views.attempt_state, name="attempt_state"),
    path("manage/exams/<uuid:session_id>/results/", views.manage_exam_results, name="manage_exam_results"),
    path(
        "manage/exams/<uuid:session_id>/results/<str:target>/<str:action>/",
        views.manage_result_release, name="manage_result_release",
    ),
]
