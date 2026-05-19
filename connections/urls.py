from django.urls import path
from . import views

urlpatterns = [
    path('',              views.ConnectionsGame, name='connections'),
    path('<int:puzzle_id>/', views.ConnectionsGame, name='connections_puzzle'),
]