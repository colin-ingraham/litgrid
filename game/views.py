from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
from library.models import Book
from . import validation

class DailyGame(View):
    def get(self, request):
        
        row_categories, col_categories = get_cell_categories()
        context = {
            'row_categories': row_categories,
            'col_categories': col_categories,
        }

        return render(request, "game/daily.html", context)

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

def get_cell_categories():
    row_categories = [
            "Fantasy",
            "Historical Fiction",
            "Literary Fiction",
        ]
        
    col_categories = [
            "Author with abbreviation in name (i.e. A.J. Watkins)",
            "Books from the 19th Century",
            "Books under 200 pages",
        ]
    return row_categories, col_categories

def get_category_codes():
    row_codes = [
            "SFantasy",
            "SHistorical",
            "SLiterary",
        ]
        
    col_codes = [
            "Aabr",
            "Tc19",
            "Lu200",
        ]
    return row_codes, col_codes


# This view will validate that the book entered is correct for the given row & col the user guessed it in.
# Each col/row will have a specific symbol to represent what it is asking
# For example subject: historical fiction will be SHistorical or (subject)(seach_query)
def validate_cell(book, col_idx, row_idx):

    row_codes, col_codes = get_category_codes()
    col = col_codes[col_idx - 1]
    row = row_codes[row_idx - 1]

    col_valid = validate_cell_to_category(col, book)
    row_valid = validate_cell_to_category(row, book)
    
    if row_valid and col_valid:
        return True
    else:
        return False

def validate_cell_to_category(c, book):
    if c[0] == "S": # Category Code: Subject
        # For a subject code, we are going to simply look for the subject provided AFTER the S. If Book has subject, then valid.
        cat_subject = c[1:]
        for subject in book.subjects.all():
            if cat_subject.lower() in subject.name.lower():
                return True

            
    elif c[0] == "A": # Category Code: Author
        author_cat = c[1:]
        if author_cat == "abr":
            if validation.checkAuthorAbbreviation(book.author.name):
                return True
            

    elif c[0] == "T": # Category Code: Time
        if c[1] == "c": # Time Period: Century
            century = c[2:]
            century = int(century) - 1
            if str(book.publish_year)[:2] == str(century):
                return True


    elif c[0] == "L": # Category Code: Length
        if c[1] == "u": # Length under x
            max_length = int(c[2:])
            if book.page_count < max_length:
                return True
        elif c[1] == "o": # Length over x
            min_length = c[2:]
            if book.page_count > min_length:
                return True
    return False