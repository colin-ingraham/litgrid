import requests
import json
import time
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.db import transaction
from django.conf import settings

from .models import Book, Author, Subject
from game import views
from datetime import datetime, date

GOOGLE_BOOKS_API_KEY = getattr(settings, 'GOOGLE_BOOKS_API_KEY', '')
GOOGLE_BOOKS_URL     = "https://www.googleapis.com/books/v1/volumes"
OPENLIBRARY_URL      = "https://openlibrary.org/search.json"
OL_COVERS_URL        = "https://covers.openlibrary.org/b"
MAX_RETRIES          = 3


# ── Utility ───────────────────────────────────────────────────────────────────

def get_or_create_author(name):
    author, created = Author.objects.get_or_create(name=name)
    return author

def get_or_create_subjects(subject_list):
    subject_objects = []
    for subject_name in subject_list:
        clean_name = subject_name.strip().title()
        if clean_name:
            subject, _ = Subject.objects.get_or_create(
                name__iexact=clean_name,
                defaults={'name': clean_name}
            )
            subject_objects.append(subject)
    return subject_objects

def fetch_ol_cover(isbn=None, title=None):
    """
    Fallback cover from Open Library — only called when Google has no cover.
    Verifies the image is real via Content-Length (OL returns a 1×1 GIF ~807
    bytes for missing covers).
    """
    headers = {'User-Agent': 'Litgrid/1.0 (contact@example.com)'}

    if isbn:
        url = f"{OL_COVERS_URL}/isbn/{isbn}-L.jpg"
        try:
            head = requests.head(url, headers=headers, timeout=4, allow_redirects=True)
            if head.status_code == 200 and int(head.headers.get('Content-Length', 0)) > 1000:
                return url
        except Exception:
            pass

    if title:
        try:
            params = {'q': title, 'limit': 1, 'fields': 'cover_i'}
            docs   = requests.get(OPENLIBRARY_URL, params=params, headers=headers, timeout=5).json().get('docs', [])
            if docs and docs[0].get('cover_i'):
                return f"{OL_COVERS_URL}/id/{docs[0]['cover_i']}-L.jpg"
        except Exception:
            pass

    return None

def fetch_ol_data(title, isbn=None):
    """
    Fetches publish year and subjects from Open Library.
    Does NOT fetch covers — Google's cover is used directly.
    """
    headers = {'User-Agent': 'Litgrid/1.0 (contact@example.com)'}
    result  = {'year': None, 'subjects': []}
    doc     = None

    if isbn:
        try:
            params = {'limit': 1, 'fields': 'key,first_publish_year,subject', 'isbn': isbn}
            docs   = requests.get(OPENLIBRARY_URL, params=params, headers=headers, timeout=5).json().get('docs', [])
            if docs:
                doc = docs[0]
        except Exception:
            pass

    if not doc:
        try:
            params = {'limit': 1, 'fields': 'key,first_publish_year,subject', 'q': title}
            docs   = requests.get(OPENLIBRARY_URL, params=params, headers=headers, timeout=5).json().get('docs', [])
            if docs:
                doc = docs[0]
        except Exception:
            pass

    if doc:
        year = doc.get('first_publish_year')
        if year and isinstance(year, int):
            result['year'] = year

        result['subjects'] = doc.get('subject', [])

        if not result['subjects'] and 'key' in doc:
            try:
                work_resp = requests.get(
                    f"https://openlibrary.org{doc['key']}.json",
                    headers=headers, timeout=5
                )
                if work_resp.status_code == 200:
                    result['subjects'] = [
                        s if isinstance(s, str) else s.get('name', '')
                        for s in work_resp.json().get('subjects', [])
                        if isinstance(s, (str, dict))
                    ][:10]
            except Exception:
                pass

    return result


def format_book_data(volume_info, volume_id):
    """Extracts data from Google Books API response."""
    authors_list = volume_info.get('authors', [])
    author_name  = authors_list[0] if authors_list else 'Unknown Author'

    published_date = volume_info.get('publishedDate', '')
    publish_year   = None
    if published_date and len(published_date) >= 4:
        try:
            publish_year = int(published_date[:4])
        except ValueError:
            pass

    image_links = volume_info.get('imageLinks', {})
    thumbnail   = image_links.get('thumbnail') or image_links.get('smallThumbnail')
    if thumbnail:
        thumbnail = thumbnail.replace('http://', 'https://')
    cover_url = thumbnail or ''  # empty string = no cover, triggers OL fallback on save

    isbn = None
    for identifier in volume_info.get('industryIdentifiers', []):
        if identifier.get('type') in ('ISBN_13', 'ISBN_10'):
            val = identifier.get('identifier')
            if val and len(val) <= 13:
                isbn = val
                break

    return {
        'google_book_id': volume_id,
        'title':          volume_info.get('title', 'Unknown Title'),
        'author_name':    author_name,
        'publish_year':   publish_year,
        'page_count':     volume_info.get('pageCount', 0),
        'thumbnail_url':  cover_url,
        'isbn':           isbn,
        'subjects':       volume_info.get('categories', []),
    }

def format_for_frontend(book_obj, source='local'):
    """
    Returns a dict for frontend search results.
    Prefers cover_override, then thumbnail_url, then placeholder.
    """
    PLACEHOLDER = 'https://placehold.co/55x80/4a4a4a/ffffff?text=N/A'
    if source == 'local':
        cover = (
            getattr(book_obj, 'cover_override', None)
            or book_obj.thumbnail_url
            or PLACEHOLDER
        )
        return {
            'id':     book_obj.google_book_id,
            'title':  book_obj.title,
            'author': book_obj.author.name if book_obj.author else 'Unknown Author',
            'cover':  cover.replace('http://', 'https://'),
        }
    else:
        cover = book_obj.get('thumbnail_url') or PLACEHOLDER
        return {
            'id':     book_obj['google_book_id'],
            'title':  book_obj['title'],
            'author': book_obj['author_name'],
            'cover':  cover,
        }


# ── Search ────────────────────────────────────────────────────────────────────

@require_GET
def book_search(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 4:
        return JsonResponse([], safe=False)

    cached = Book.objects.filter(title__iexact=query).select_related('author')
    if cached.exists():
        return JsonResponse([format_for_frontend(b) for b in cached[:5]], safe=False)

    params = {'q': query, 'maxResults': 15, 'key': GOOGLE_BOOKS_API_KEY}
    data   = None
    for attempt in range(MAX_RETRIES):
        if data: break
        try:
            resp = requests.get(GOOGLE_BOOKS_URL, params=params, timeout=5)
            if resp.status_code == 503:
                time.sleep(2 ** attempt)
                continue
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException:
            break

    if not data or 'items' not in data:
        return JsonResponse([], safe=False)

    seen, results = set(), []
    for item in data['items']:
        vid  = item.get('id')
        info = item.get('volumeInfo', {})
        if not vid or not info: continue
        bd  = format_book_data(info, vid)
        key = (bd['title'].strip().lower(), bd['author_name'].strip().lower())
        if key not in seen:
            seen.add(key)
            results.append(format_for_frontend(bd, source='api'))

    results.sort(key=lambda b: (
        0 if b['title'].lower().strip() == query.lower().strip() else
        1 if b['title'].lower().strip().startswith(query.lower().strip()) else 2
    ))
    return JsonResponse(results[:10], safe=False)


# ── Save & Validate (original Litgrid game) ───────────────────────────────────

@require_POST
def save_and_validate_guess(request):
    try:
        data        = json.loads(request.body)
        book_id     = data.get('book_id')
        row         = int(data.get('row'))
        col         = int(data.get('col'))
        date_str    = data.get('puzzle_date')
        target_date = (
            datetime.strptime(date_str, "%Y-%m-%d").date()
            if date_str else date.today()
        )
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid data'}, status=400)

    book = None
    try:
        book = Book.objects.get(google_book_id=book_id)
    except Book.DoesNotExist:
        try:
            resp      = requests.get(f"{GOOGLE_BOOKS_URL}/{book_id}?key={GOOGLE_BOOKS_API_KEY}", timeout=5)
            resp.raise_for_status()
            vol_data  = resp.json()
            book_info = format_book_data(vol_data['volumeInfo'], vol_data['id'])

            existing = Book.objects.filter(
                title__iexact=book_info['title'],
                author__name__iexact=book_info['author_name']
            ).select_related('author').first()

            if existing:
                book = existing
            else:
                ol_data = fetch_ol_data(book_info['title'], isbn=book_info['isbn'])
                if ol_data['year']:
                    book_info['publish_year'] = ol_data['year']

                # Only use OL cover if Google has none
                if not book_info['thumbnail_url']:
                    ol_cover = fetch_ol_cover(isbn=book_info['isbn'], title=book_info['title'])
                    if ol_cover:
                        book_info['thumbnail_url'] = ol_cover

                combined = list(set(book_info['subjects'] + ol_data['subjects']))

                with transaction.atomic():
                    author_obj = get_or_create_author(book_info['author_name'])
                    book, _    = Book.objects.update_or_create(
                        google_book_id=book_info['google_book_id'],
                        defaults={
                            'title':         book_info['title'],
                            'author':        author_obj,
                            'publish_year':  book_info['publish_year'],
                            'page_count':    book_info['page_count'],
                            'thumbnail_url': book_info['thumbnail_url'],
                            'isbn':          book_info['isbn'],
                        }
                    )
                    book.subjects.set(get_or_create_subjects(combined))
        except Exception:
            import traceback; traceback.print_exc()
            return JsonResponse({'is_correct': False, 'message': 'Could not verify and save book details.'})

    is_correct = views.validate_cell(book, col, row, target_date=target_date)
    return JsonResponse({'is_correct': is_correct, 'message': 'Book selected and saved.', 'book_title': book.title})