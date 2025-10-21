from django.contrib import admin
from django.http import HttpResponse
from django.urls import path
from django.urls import include



def health(_):
    return HttpResponse("DMOJ-Lite starter is running ✅")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", health, name="health"),
]
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("judge.urls")),
]
