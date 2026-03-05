# arena/urls.py
from django.urls import path
from . import views

app_name = "arena"

urlpatterns = [
    path("", views.game_list, name="game_list"),
    path("robot/", views.robot_play, name="robot_play"),
    #path("snake/", views.snake_play, name="snake_play"),
]

