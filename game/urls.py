from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.DailyGame.as_view(), name="daily_game"),
    path('book-search/', views.BookSearchData, name="book-search"),

]
