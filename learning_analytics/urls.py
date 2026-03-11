from django.urls import path

from . import api, views

app_name = "learning_analytics"

urlpatterns = [
    path("admin/", views.admin_learning_dashboard, name="admin_dashboard"),
    path("admin/students/", views.student_dashboard, name="student_dashboard"),
    path("admin/user/<int:user_id>/", views.user_learning_profile, name="user_learning_profile"),
    path("admin/class/", views.class_dashboard, name="class_dashboard"),
    path("admin/topics/", views.topic_dashboard, name="topic_dashboard"),
    path("admin/contests/", views.contest_dashboard, name="contest_dashboard"),
    path("api/student/<int:id>/analytics", api.student_analytics, name="student_analytics"),
    path("api/student/<int:id>/skills", api.student_skills, name="student_skills"),
    path("api/student/<int:id>/weakness", api.student_weakness, name="student_weakness"),
    path("api/student/<int:id>/recommendations", api.student_recommendations, name="student_recommendations"),
    path("api/student/<int:id>/learning-path", api.student_learning_path, name="student_learning_path"),
    path("api/student/<int:id>/contest-analysis", api.student_contest_analysis, name="student_contest_analysis"),
    path("api/student/<int:id>/training_plan", api.student_training_plan, name="student_training_plan"),
    path("api/student/<int:id>/weak_skills", api.student_weak_skills, name="student_weak_skills"),
    path("api/admin/user/<int:id>/learning_profile", api.admin_user_learning_profile, name="admin_user_learning_profile"),
]
