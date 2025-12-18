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
from game import views

GOOGLE_BOOKS_API_KEY = getattr(settings, 'GOOGLE_BOOKS_API_KEY', '')
GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
OPENLIBRARY_URL = "https://openlibrary.org/search.json" 
MAX_RETRIES = 3 

# --- Utility Functions ---

def get_or_create_author(name):
    author, created = Author.objects.get_or_create(name=name)
    return author

def get_or_create_subjects(subject_list):
    subject_objects = []
    for subject_name in subject_list:
        # Basic cleaning: Title case the subject to avoid "war" vs "War" duplicates
        clean_name = subject_name.strip().title()
        if len(clean_name) > 0:
            subject, created = Subject.objects.get_or_create(
                name__iexact=clean_name,
                defaults={'name': clean_name}
            )
            subject_objects.append(subject)
    return subject_objects

def fetch_ol_data(title, isbn=None):
    """
    Fetches publish year and subjects.
    Strategy:
    1. Search by ISBN.
    2. If ISBN fails (0 results), Search by Title.
    3. If search result has no subjects, fetch Work API.
    """
    headers = {
        'User-Agent': 'Litgrid/1.0 (https://github.com/colin-ingraham/litgrid; contact@example.com)'
    }
    
    result = {'year': None, 'subjects': []}
    doc = None

    # --- Step 1: Try Search by ISBN ---
    if isbn:
        try:
            params = {'limit': 1, 'fields': 'key,title,author_name,first_publish_year,subject', 'isbn': isbn}
            resp = requests.get(OPENLIBRARY_URL, params=params, headers=headers, timeout=5)
            data = resp.json()
            docs = data.get('docs', [])
            
            if docs:
                doc = docs[0]
        except Exception:
            pass # Fail silently and fall back to title

    # --- Step 2: Fallback to Title Search (if ISBN failed or wasn't provided) ---
    if not doc:
        try:
            params = {'limit': 1, 'fields': 'key,title,author_name,first_publish_year,subject', 'q': title}
            resp = requests.get(OPENLIBRARY_URL, params=params, headers=headers, timeout=5)
            data = resp.json()
            docs = data.get('docs', [])
            
            if docs:
                doc = docs[0]
        except Exception:
            pass

    # --- Step 3: Process the Document (if found) ---
    if doc:
        # Get Year
        year = doc.get('first_publish_year')
        if year and isinstance(year, int):
            result['year'] = year
        
        # Get Subjects
        result['subjects'] = doc.get('subject', [])
        
        # --- Step 4: Check for Missing Subjects (Work API Fallback) ---
        if not result['subjects'] and 'key' in doc:
            work_key = doc['key']
            
            try:
                work_url = f"https://openlibrary.org{work_key}.json"
                work_resp = requests.get(work_url, headers=headers, timeout=5)
                
                if work_resp.status_code == 200:
                    work_data = work_resp.json()
                    raw_subjects = work_data.get('subjects', [])
                    
                    clean_subjects = []
                    for s in raw_subjects:
                        if isinstance(s, str):
                            clean_subjects.append(s)
                        elif isinstance(s, dict) and 'name' in s:
                            clean_subjects.append(s['name'])
                    
                    result['subjects'] = clean_subjects[:10]
            except Exception:
                pass

    return result


def format_book_data(volume_info, volume_id):
    """Extracts data from Google Books API response."""
    authors_list = volume_info.get('authors', [])
    author_name = authors_list[0] if authors_list else 'Unknown Author'
    
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
        'publish_year': publish_year, 
        'page_count': volume_info.get('pageCount', 0),
        'thumbnail_url': cover_url,
        'isbn': isbn,
        'subjects': subjects, # This is just Google's list for now
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

    # 3. Process API Results
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
        if title == q: return 0
        if title.startswith(q): return 1
        return 2

    api_results_formatted.sort(key=rank_book)
    return JsonResponse(api_results_formatted[:10], safe=False)


# --- VALIDATION & SAVING VIEW (Updated) ---

# ... imports remain the same ...

@require_POST
def save_and_validate_guess(request):
    try:
        data = json.loads(request.body)
        book_id = data.get('book_id')
        row = int(data.get('row'))
        col = int(data.get('col'))
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid data'}, status=400)

    # --- STEP 1: Ensure Book is in Database ---
    book = None
    try:
        book = Book.objects.get(google_book_id=book_id)
    except Book.DoesNotExist:
        # Fetch from Google API
        api_url = f"{GOOGLE_BOOKS_URL}/{book_id}?key={GOOGLE_BOOKS_API_KEY}"
        
        try:
            resp = requests.get(api_url, timeout=5)
            resp.raise_for_status()
            vol_data = resp.json()
            
            book_info = format_book_data(vol_data['volumeInfo'], vol_data['id'])
            
            # Check if we already have this book via Title/Author (Soft match)
            existing_book = Book.objects.filter(
                title__iexact=book_info['title'],
                author__name__iexact=book_info['author_name']
            ).select_related('author').first()

            if existing_book:
                book = existing_book
            else:
                # --- FETCH EXTRA DATA FROM OPENLIBRARY ---
                ol_data = fetch_ol_data(book_info['title'], isbn=book_info['isbn'])
                
                # Update Year if found
                if ol_data['year']:
                    book_info['publish_year'] = ol_data['year']
                
                # MERGE SUBJECTS
                combined_subjects = list(set(book_info['subjects'] + ol_data['subjects']))

                # Proceed with saving
                with transaction.atomic():
                    author_obj = get_or_create_author(book_info['author_name'])
                    
                    # FIX: Use update_or_create to prevent IntegrityError crashes
                    book, created = Book.objects.update_or_create(
                        google_book_id=book_info['google_book_id'],
                        defaults={
                            'title': book_info['title'],
                            'author': author_obj,
                            'publish_year': book_info['publish_year'],
                            'page_count': book_info['page_count'],
                            'thumbnail_url': book_info['thumbnail_url'],
                            'isbn': book_info['isbn'],
                        }
                    )
                    
                    # Update subjects
                    subject_objects = get_or_create_subjects(combined_subjects)
                    book.subjects.set(subject_objects)
                
                print(f"Book '{book_info['title']}' saved/updated successfully.")
                
        except Exception as e:
            # FIX: Use book_id in error message since 'book' might be None
            print(f"Error saving book {book_id}: {e}")
            import traceback
            traceback.print_exc() # Helps see the full error in console
            return JsonResponse({'is_correct': False, 'message': 'Could not verify and save book details.'})

    # --- STEP 2: Validation Logic ---
    is_correct = views.validate_cell(book, col, row)
    
    return JsonResponse({
        'is_correct': is_correct,
        'message': 'Book selected and saved.',
        'book_title': book.title
    })