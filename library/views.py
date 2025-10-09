from django.shortcuts import render, redirect
from django.views import View
from .models import Book
# Create your views here.

class SearchView(View):
    def get(self, request):
        return render(request, "library/search_library.html")
    def post(self, request):
        title_input = request.POST.get('user_text_input', "")
        book = Book.objects.get(title=title_input)
        url = f"https://covers.openlibrary.org/b/id/{book.cover_id}-M.jpg"
        return render(request, "library/book_details.html", {
            "title": book.title,
            "author": book.author,
            "url": url,

        }
        )

