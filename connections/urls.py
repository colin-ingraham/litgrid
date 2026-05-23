from django.urls import path
from . import views

urlpatterns = [
    path('',                                        views.ConnectionsGame,   name='connections'),
    path('<int:puzzle_id>/',                        views.ConnectionsGame,   name='connections_puzzle'),
    path('api/complete/<int:puzzle_id>/',           views.save_completion,   name='connections_complete'),
    path('api/progress/<int:puzzle_id>/',           views.save_progress,     name='connections_progress'),
]