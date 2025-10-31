from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
from library.models import Book

class DailyGame(View):
    def get(self, request):
        return render(request, "game/daily.html")

def BookSearchData(request):
    if request.method == 'POST':
        title_input = request.POST.get('user_text_input', "").strip()
        try:
            book = Book.objects.get(title__iexact=title_input)
            url = f"https://covers.openlibrary.org/b/id/{book.cover_id}-M.jpg"
            return JsonResponse({
                "success": True,
                "title": book.title,
                "author": book.author.name,
                "url": url,
            })
        except Book.DoesNotExist:
            return JsonResponse({
                "success": False, 
                "error": f"Book '{title_input}' not found in database."
            }, status=404)
    return JsonResponse({"success": False, "error": "An error occurred."}, status=500)
