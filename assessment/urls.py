from django.urls import path

from assessment import views


app_name = "assessment"

urlpatterns = [
    path("", views.exam_list, name="exam_list"),
]
