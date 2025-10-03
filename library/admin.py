from django.contrib import admin
from .models import Book, Author, Subject
# Register your models here.

class BookAdmin(admin.ModelAdmin):
    readonly_fields=("subjects", "cover_id", "key")


admin.site.register(Book, BookAdmin)
admin.site.register(Author)
admin.site.register(Subject)