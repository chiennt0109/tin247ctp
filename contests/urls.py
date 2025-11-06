from django.urls import path
from . import views
app_name = "contests" 
urlpatterns = [
    path('', views.contest_list, name='contest_list'),
    path('<int:contest_id>/', views.contest_detail, name='contest_detail'),
    path('<int:contest_id>/rank/', views.contest_rank, name='contest_rank'),
    path("<int:contest_id>/ai_report/", views.contest_ai_report, name="contest_ai_report"),
]
