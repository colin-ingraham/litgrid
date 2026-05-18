from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.DailyGame.as_view(), name="daily_game"),
    path('book-search/', views.BookSearchData, name="book-search"),
    path('api/archive-list/', views.get_archive_list, name='archive-list'),
    path('puzzle/<str:date_str>/', views.DailyGame.as_view(), name='daily-puzzle-date'),
]
