from django.contrib import admin
from .models import Book, Author, Subject
# Register your models here.


admin.site.register(Author)
admin.site.register(Subject)

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    search_fields = ('title', 'author__name')