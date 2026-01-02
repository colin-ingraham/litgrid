from django.contrib import admin
from game.models import Category, DailyPuzzle
# Register your models here.
admin.site.register(Category)
admin.site.register(DailyPuzzle)