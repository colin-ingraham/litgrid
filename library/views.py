import requests
import json
import time 
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.db import transaction 
from django.core.exceptions import ObjectDoesNotExist 
from django.conf import settings 
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import Book, Author, Subject 

GOOGLE_BOOKS_API_KEY = getattr(settings, 'GOOGLE_BOOKS_API_KEY', '')
GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
OPENLIBRARY_URL = "https://openlibrary.org/search.json" # New URL for Open Library
MAX_RETRIES = 3 

# --- Utility Functions ---

def get_or_create_author(name):
    author, created = Author.objects.get_or_create(name=name)
    return author

def get_or_create_subjects(subject_list):
    subject_objects = []
    for subject_name in subject_list:
        subject, created = Subject.objects.get_or_create(
            name__iexact=subject_name,
            defaults={'name': subject_name}
        )
        subject_objects.append(subject)
    return subject_objects

def fetch_first_publish_year_from_ol(title):
    """
    Fetches the first publish year from the OpenLibrary API using the book's title.
    Returns the year (int) or None if not found or on error.
    """
    headers = {
        # Required User-Agent for ethical API usage
        'User-Agent': 'Litgrid/1.0 (https://github.com/colin-ingraham/litgrid; contact@example.com)'
    }
    params = {
        'q': title,
        'limit': 1 # Only need the top result
    }
    
    try:
        response = requests.get(OPENLIBRARY_URL, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        documents = data.get('docs', [])
        if documents:
            # Open Library's 'first_publish_year' is exactly what we need
            year = documents[0].get('first_publish_year')
            if year and isinstance(year, int):
                return year
    except requests.exceptions.RequestException as e:
        print(f"OpenLibrary API Error for '{title}': {e}")
    except Exception as e:
        print(f"Error processing OpenLibrary data for '{title}': {e}")
        
    return None


def format_book_data(volume_info, volume_id):
    """Extracts data from Google Books API response."""
    # ... (Keep existing logic for authors, cover, subjects, etc.) ...
    authors_list = volume_info.get('authors', [])
    author_name = authors_list[0] if authors_list else 'Unknown Author'
    
    # NOTE: We keep the Google publish_year here as a fallback, but the OL year will overwrite it later.
    published_date = volume_info.get('publishedDate', '')
    publish_year = None
    if published_date and len(published_date) >= 4:
        try:
            publish_year = int(published_date[:4])
        except ValueError:
            pass
            
    image_links = volume_info.get('imageLinks', {})
    thumbnail = image_links.get('thumbnail') or image_links.get('smallThumbnail')
    cover_url = thumbnail or 'https://placehold.co/55x80/4a4a4a/ffffff?text=N/A'
    
    subjects = volume_info.get('categories', [])
    
    isbn_raw = volume_info.get('industryIdentifiers', [{}])
    isbn = None
    if isbn_raw:
        for identifier in isbn_raw:
            if identifier.get('type') in ('ISBN_13', 'ISBN_10'):
                identifier_val = identifier.get('identifier', None)
                if identifier_val and len(identifier_val) <= 13:
                    isbn = identifier_val
                    break
    
    return {
        'google_book_id': volume_id,
        'title': volume_info.get('title', 'Unknown Title'),
        'author_name': author_name,
        'publish_year': publish_year, # Google's (potentially inaccurate) year
        'page_count': volume_info.get('pageCount', 0),
        'thumbnail_url': cover_url,
        'isbn': isbn,
        'subjects': subjects,
    }

def format_for_frontend(book_obj, source='local'):
    if source == 'local':
        return {
            'id': book_obj.google_book_id,
            'title': book_obj.title,
            'author': book_obj.author.name if book_obj.author else 'Unknown Author',
            'cover': book_obj.thumbnail_url or 'https://placehold.co/55x80/4a4a4a/ffffff?text=N/A',
        }
    else:
        return {
            'id': book_obj['google_book_id'],
            'title': book_obj['title'],
            'author': book_obj['author_name'],
            'cover': book_obj['thumbnail_url'] or 'https://placehold.co/55x80/4a4a4a/ffffff?text=N/A',
        }

# --- SEARCH VIEW (Unchanged) ---

@require_GET
def book_search(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 4: 
        return JsonResponse([], safe=False)

    final_results = []
    
    # 1. Check Local Cache
    cached_books = Book.objects.filter(title__iexact=query).select_related('author')
    if cached_books.exists():
        for book in cached_books[:5]:
            final_results.append(format_for_frontend(book, source='local'))
        return JsonResponse(final_results, safe=False)

    # 2. API Search
    params = {
        'q': query, 
        'maxResults': 15, 
        'key': GOOGLE_BOOKS_API_KEY, 
    }
    
    data = None
    for attempt in range(MAX_RETRIES):
        if data: break
        try:
            response = requests.get(GOOGLE_BOOKS_URL, params=params, timeout=5)
            if response.status_code == 503:
                time.sleep(2 ** attempt) 
                continue
            response.raise_for_status() 
            data = response.json()
        except requests.exceptions.RequestException:
            break 
            
    if not data or 'items' not in data:
        return JsonResponse([], safe=False)

    # 3. Process API Results (De-duplication only, NO SAVING)
    seen_titles = set()
    api_results_formatted = []
    
    for item in data['items']:
        volume_id = item.get('id')
        volume_info = item.get('volumeInfo', {})
        if not volume_id or not volume_info: continue
        
        book_data = format_book_data(volume_info, volume_id)
        
        title_author_key = (book_data['title'].strip().lower(), book_data['author_name'].strip().lower())
        
        if title_author_key not in seen_titles:
            seen_titles.add(title_author_key)
            api_results_formatted.append(format_for_frontend(book_data, source='api'))

    # 4. CUSTOM RANKING LOGIC
    def rank_book(book_dict):
        title = book_dict['title'].lower().strip()
        q = query.lower().strip()
        
        if title == q:
            return 0
        if title.startswith(q):
            return 1
        return 2

    api_results_formatted.sort(key=rank_book)
    
    return JsonResponse(api_results_formatted[:10], safe=False)


# --- VALIDATION & SAVING VIEW ---

@require_POST
def save_and_validate_guess(request):
    try:
        data = json.loads(request.body)
        book_id = data.get('book_id')
        row = int(data.get('row'))
        col = int(data.get('col'))
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid data'}, status=400)

    # --- STEP 1: Ensure Book is in Database (The "Save on Select" Logic) ---
    book = None
    try:
        # Check 1: Check if book is already in cache by Google Book ID (fastest check)
        book = Book.objects.get(google_book_id=book_id)
    except Book.DoesNotExist:
        # If not found by ID, we need to fetch the data from API
        api_url = f"{GOOGLE_BOOKS_URL}/{book_id}?key={GOOGLE_BOOKS_API_KEY}"
        
        try:
            resp = requests.get(api_url, timeout=5)
            resp.raise_for_status()
            vol_data = resp.json()
            
            book_info = format_book_data(vol_data['volumeInfo'], vol_data['id'])
            
            # FIX: Check 2: Check for existing book by Title and Author
            existing_book = Book.objects.filter(
                title__iexact=book_info['title'],
                author__name__iexact=book_info['author_name']
            ).select_related('author').first()

            if existing_book:
                book = existing_book
                print(f"Found existing book '{book.title}' by Title/Author. Using existing record.")
            else:
                # --- CRITICAL FIX: OVERWRITE publish_year with OpenLibrary data ---
                ol_year = fetch_first_publish_year_from_ol(book_info['title'])
                if ol_year:
                    print(f"Found accurate publish year {ol_year} from OpenLibrary for '{book_info['title']}'.")
                    book_info['publish_year'] = ol_year # Use OL year instead of Google's year

                # Proceed with saving the new, unique book
                with transaction.atomic():
                    author_obj = get_or_create_author(book_info['author_name'])
                    book = Book.objects.create(
                        google_book_id=book_info['google_book_id'],
                        title=book_info['title'],
                        author=author_obj,
                        publish_year=book_info['publish_year'], # This is now the OL year (if found)
                        page_count=book_info['page_count'],
                        thumbnail_url=book_info['thumbnail_url'],
                        isbn=book_info['isbn'],
                    )
                    subject_objects = get_or_create_subjects(book_info['subjects'])
                    book.subjects.set(subject_objects)
                print(f"New book {book_id} saved successfully with OL year.")
                
        except Exception as e:
            print(f"Error saving book {book_id}: {e}")
            return JsonResponse({'is_correct': False, 'message': 'Could not verify and save book details.'})

    # --- STEP 2: TEMPORARY Validation Logic ---
    is_correct = True # Always True for now, as requested.
    validate_cell(book)
    
    return JsonResponse({
        'is_correct': is_correct,
        'message': 'Book selected and saved (Validation skipped).',
        'book_title': book.title
    })

# This view will validate that the book entered is correct for the given row & col the user guessed it in.
# While we could hardcode the first subjects, I'd like to at least provide some modularity.
# Each col/row will have a specific symbol to represent what it is asking
# For example subject: historical fiction will be SHistorical or (subject)(seach_query)
def validate_cell(book, col, row):
    col_valid = False
    row_valid = False

    # Col Validation
    if col[0] == "S": # Category Code: Subject
        # For a subject code, we are going to simply look for the subject provided AFTER the S. If Book has subject, then valid.
        cat_subject = col[1:]
        for subject in book.subjects:
            if subject in cat_subject:
                col_valid = True
    elif col[0] == "A": # Category Code: Author
        pass
    elif col[0] == "T": # Category Code: Time
        pass

    # Row Validation
    if row[0] == "S": # Category Code: Subject
        # For a subject code, we are going to simply look for the subject provided AFTER the S. If Book has subject, then valid.
        cat_subject = row[1:]
        for subject in book.subjects:
            if subject in cat_subject:
                row_valid = True
    elif row[0] == "A": # Category Code: Author
        pass
    elif row[0] == "T": # Category Code: Time
        pass
    
    if row_valid and col_valid:
        return True
    else:
        return False