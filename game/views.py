from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
from library.models import Book

class DailyGame(View):
    def get(self, request):
        return render(request, "game/daily.html")

def BookSearchData(request):
    if request.method == 'POST':
        title_input = request.POST.get('user_text_input', "")
        book = Book.objects.get(title=title_input)
        if book:
            url = f"https://covers.openlibrary.org/b/id/{book.cover_id}-M.jpg"
            book_data = {
                "title": book.title,
                "author": book.author,
                "url": url,
            }
            return JsonResponse(book_data)
        else:
            return JsonResponse({"success": False, "error": "Book not found."}, status=404)
    return JsonResponse({"success": False, "error": "An error occurred."}, status=500)
