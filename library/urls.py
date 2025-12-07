from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('book-search/', views.book_search, name='book-search'),
    path('validate-guess/', views.save_and_validate_guess, name='validate-guess'),
]