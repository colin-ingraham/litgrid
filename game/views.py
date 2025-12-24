from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
from library.models import Book
from . import validation
import calendar

"""
The Litgrid Category Validation uses a special code system to track the subjects in an efficient manner.

Below is the documentation to decrypt these codes.

Subject Codes (S):
SGenre

Time Codes (T):
Tc - Time period: century
Td - Time period: decade
TpXXXXYYYY - Time period: 19391945
Tm___ - Time Miscellanious (leap)

Length Codes (L):
Lu - Length Under
Lo - Length Over

Name/Title Codes (N):
Nw1 - Name, word, 1 (length)
Nw7+ - Name, word, 7 (length), + (or more)
Ns___ - Name, starts (with), word
Nc___ - Name, contains, category

Author Codes (A):
A___ - Category first 3 letters
AN__ - Author, has first Name, name (John, Mary, etc)



"""
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
            
        elif c[1] == "d": # Time Period: Decade
            century = c[2]
            if int(century) > 2:
                century = "1" + century
            else:
                century = century + "0"
            decade = century + c[3]
            if str(book.publish_year)[:3] == str(decade):
                return True
        
        elif c[1] == "p": 
            year1 = c[2:6]
            year2 = c[6:]
            if book.publish_year >= int(year1) and book.publish_year <= int(year2):
                return True
            
        elif c[1] == "m":
            if c[2:] == "leap":
                if calendar.isleap(book.publish_year):
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
            
    elif c[0] == "N": # Category Code: Name/Title
        title = book.title.lower()

        if c[1] == "w": # Word count Logic
            words = title.split()
            count = len(words)
            
            target = c[2]
            if c[3] == "+": # Word count is x or greater
                if count >= target: 
                    return True
            else:
                if count == target: 
                    return True

        if c[1] == "c": # Contains x in title

            cat_type = c[2:]
            keywords = set()

            # For "Contains" checks, we need clean words to avoid partial matches 
            # (e.g. preventing "Scared" from matching "Red")
            import string
            translator = str.maketrans('', '', string.punctuation)
            # This creates a set of all individual words in the title, stripped of punctuation
            title_words = set(title.translate(translator).split())

            if cat_type == "num": # Ncnum
                # Check for actual digits first (e.g. "1984")
                if any(char.isdigit() for char in title):
                    return True
                # Number words
                keywords = {
                    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", 
                    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", 
                    "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", 
                    "eighty", "ninety", "hundred", "thousand", "million", "billion"
                }
            elif cat_type == "col": # Nccol
                keywords = {
                    "red", "blue", "green", "yellow", "gold", "silver", "black", "white", 
                    "orange", "purple", "brown", "pink", "gray", "grey", "violet", "indigo", 
                    "scarlet", "crimson", "emerald", "ruby", "sapphire"
                }

            elif cat_type == "fam": # Ncfam
                keywords = {
                    "mother", "father", "sister", "brother", "daughter", "son", "aunt", "uncle", 
                    "wife", "husband", "mom", "dad", "parent", "child", "grandmother", "grandfather", 
                    "grandma", "grandpa", "niece", "nephew", "cousin", "stepmother", "stepfather"
                }

            elif cat_type == "sea": # Ncsea
                keywords = {"spring", "summer", "autumn", "fall", "winter"}

            # Efficiently check if ANY keyword exists in the title's word set
            # !isdisjoint returns True if there is at least one common element
            if not keywords.isdisjoint(title_words):
                return True

        if c[1] == "s": # Start Word is x
            start_word = c[2:]
            if title.startswith(start_word):
                return True


    return False

