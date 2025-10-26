from django.urls import path
from . import views

urlpatterns = [
    path('my/', views.my_submissions, name='my_submissions'),
    path('<int:problem_id>/submit/', views.submission_create, name='submission_create'),
]
