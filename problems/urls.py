# path: problems/urls.py
from django.urls import path
from . import views, views_admin
from . import views_profile

urlpatterns = [
    path('', views.problem_list, name="problem_list"),
    path('<int:pk>/', views.problem_detail, name="problem_detail"),

    path("profile/", views_profile.profile_view, name="profile"),
    path("change-password/", views_profile.change_password_view, name="change_password"),

    # AI cho user
    path('<int:pk>/ai_hint/', views.ai_hint, name="ai_hint"),
    path('<int:pk>/ai_debug/', views.ai_debug, name="ai_debug"),
    path('<int:pk>/ai_recommend/', views.ai_recommend, name="ai_recommend"),
    path('ai_learning_path/', views.ai_learning_path, name="ai_learning_path"),
    path("<int:pk>/ai_hint_random/", views.ai_hint_random, name="ai_hint_random"),

    path("<int:pk>/ai_solution/", views.get_solution, name="ai_solution"),
    path("<int:pk>/ai_next/", views.get_next_recommendation, name="ai_next"),
    path("<int:pk>/ai_learn/", views.get_learning_path, name="ai_learning_path"),


    # AI cho admin
    path('ai_suggest_tags/', views_admin.ai_suggest_tags, name="ai_suggest_tags"),
    path('ai_analyze_problem/', views_admin.ai_analyze_problem, name="ai_analyze_problem"),
    path("admin_ai_generate/", views.admin_ai_generate),
    path("admin_ai_samples/", views.admin_ai_samples),
    path("admin_ai_check/", views.admin_ai_check),
    path("<int:pk>/ai_solution/", views.get_solution, name="ai_solution"),

]
