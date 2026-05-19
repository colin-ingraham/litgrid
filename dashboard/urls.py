from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('',                      views.dashboard_home,          name='home'),
    path('create/connections/',   views.create_connections,      name='create_connections'),
    path('api/save-puzzle/',      views.save_connections_puzzle, name='save_puzzle'),
]