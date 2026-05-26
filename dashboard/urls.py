from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('',                                        views.dashboard_home,           name='home'),
    path('create/connections/',                     views.create_connections,       name='create_connections'),
    path('edit/connections/<int:draft_id>/',        views.edit_connections,         name='edit_connections'),
    path('edit/puzzle/<int:puzzle_id>/',            views.edit_puzzle,              name='edit_puzzle'),
    path('api/save-puzzle/',                        views.save_connections_puzzle,  name='save_puzzle'),
    path('api/update-puzzle/<int:puzzle_id>/',      views.update_connections_puzzle, name='update_puzzle'),
    path('api/draft/save/',                         views.save_draft,               name='save_draft'),
    path('api/draft/delete/<int:draft_id>/',        views.delete_draft,             name='delete_draft'),
]