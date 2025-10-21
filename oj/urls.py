from django.contrib import admin
from django.http import HttpResponse
from django.urls import path

def health(_):
    return HttpResponse("DMOJ-Lite starter is running ✅")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", health, name="health"),
]
