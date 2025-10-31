from django.urls import path
from . import views

urlpatterns = [
    path("<int:problem_id>/submit/", views.submission_create, name="submission_create"),
    path("<int:submission_id>/", views.submission_detail, name="submission_detail"),
]
