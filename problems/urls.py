# path: problems/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.problem_list, name='problem_list'),
    path('<int:pk>/', views.problem_detail, name='problem_detail'),

    # 🌐 AI hỗ trợ
    path('<int:pk>/ai_hint/', views.ai_hint_real, name='ai_hint'),
    path('<int:pk>/ai_debug/', views.ai_debug, name='ai_debug'),
    path('<int:pk>/ai_recommend/', views.ai_recommend, name='ai_recommend'),

    # 🧭 Lộ trình học miễn phí
    path('ai_learning_path/', views.ai_learning_path, name='ai_learning_path'),
]
