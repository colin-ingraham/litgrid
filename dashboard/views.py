import json
import requests

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.conf import settings

from library.models import Book
from library.views import (
    GOOGLE_BOOKS_URL,
    format_book_data,
    fetch_ol_data,
    get_or_create_author,
    get_or_create_subjects,
)
from .models import ConnectionsPuzzle, ConnectionsGroup, ConnectionsBookEntry


# --- Constants ---------------------------------------------------------------

DIFFICULTY_LEVELS = [
    {'order': 0, 'difficulty': 1, 'name': 'Easy',   'color': '#e8c84a'},
    {'order': 1, 'difficulty': 2, 'name': 'Medium',  'color': '#6aaa64'},
    {'order': 2, 'difficulty': 3, 'name': 'Hard',    'color': '#4a90d9'},
    {'order': 3, 'difficulty': 4, 'name': 'Expert',  'color': '#9b59b6'},
]


# --- Utility -----------------------------------------------------------------

def _get_or_fetch_book(google_book_id):
    """
    Return a library.Book for the given google_book_id.
    Fetches from Google Books + OpenLibrary and saves if not already in the DB.
    Returns (book, error_string). One will always be None.
    """
    book = Book.objects.filter(google_book_id=google_book_id).first()
    if book:
        return book, None

    api_url = f"{GOOGLE_BOOKS_URL}/{google_book_id}?key={getattr(settings, 'GOOGLE_BOOKS_API_KEY', '')}"
    try:
        resp = requests.get(api_url, timeout=5)
        resp.raise_for_status()
        vol_data = resp.json()
        book_info = format_book_data(vol_data['volumeInfo'], vol_data['id'])
    except Exception as e:
        return None, f"Could not fetch book '{google_book_id}' from Google Books: {e}"

    existing = Book.objects.filter(
        title__iexact=book_info['title'],
        author__name__iexact=book_info['author_name'],
    ).select_related('author').first()
    if existing:
        return existing, None

    ol_data = fetch_ol_data(book_info['title'], isbn=book_info.get('isbn'))
    if ol_data['year']:
        book_info['publish_year'] = ol_data['year']
    combined_subjects = list(set(book_info['subjects'] + ol_data['subjects']))

    try:
        with transaction.atomic():
            author_obj = get_or_create_author(book_info['author_name'])
            book, _ = Book.objects.update_or_create(
                google_book_id=book_info['google_book_id'],
                defaults={
                    'title':         book_info['title'],
                    'author':        author_obj,
                    'publish_year':  book_info['publish_year'],
                    'page_count':    book_info['page_count'],
                    'thumbnail_url': book_info['thumbnail_url'],
                    'isbn':          book_info.get('isbn'),
                },
            )
            book.subjects.set(get_or_create_subjects(combined_subjects))
    except Exception as e:
        return None, f"Could not save book to database: {e}"

    return book, None


# --- Views -------------------------------------------------------------------

@login_required
def dashboard_home(request):
    puzzles = ConnectionsPuzzle.objects.select_related('created_by').order_by('-id')[:20]
    context = {
        'puzzles': puzzles,
    }
    return render(request, 'dashboard/home.html', context)


@login_required
def create_connections(request):
    context = {
        'difficulty_levels': DIFFICULTY_LEVELS,
        'book_search_url':   '/api/book-search/',
    }
    return render(request, 'dashboard/create_connections.html', context)


@login_required
@require_POST
def save_connections_puzzle(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON.'}, status=400)

    groups_data = data.get('groups', [])

    if len(groups_data) != 4:
        return JsonResponse(
            {'success': False, 'error': 'Puzzle must have exactly 4 groups.'},
            status=400,
        )

    for i, g in enumerate(groups_data, start=1):
        if not g.get('category', '').strip():
            return JsonResponse(
                {'success': False, 'error': f'Group {i} is missing a category name.'},
                status=400,
            )
        books = g.get('books', [])
        if len(books) != 4 or any(b is None for b in books):
            return JsonResponse(
                {'success': False, 'error': f'Group {i} must have exactly 4 books selected.'},
                status=400,
            )

    # Ensure all 16 books are in the DB before opening the transaction
    resolved = []
    for group_data in groups_data:
        group_books = []
        for book_data in group_data['books']:
            book, error = _get_or_fetch_book(book_data['id'])
            if error:
                return JsonResponse({'success': False, 'error': error}, status=400)
            group_books.append(book)
        resolved.append(group_books)

    try:
        with transaction.atomic():
            puzzle = ConnectionsPuzzle.objects.create(created_by=request.user)
            for order, (group_data, books) in enumerate(zip(groups_data, resolved)):
                group = ConnectionsGroup.objects.create(
                    puzzle=puzzle,
                    category=group_data['category'].strip(),
                    difficulty=order + 1,
                    order=order,
                )
                for slot, book in enumerate(books):
                    ConnectionsBookEntry.objects.create(group=group, book=book, slot=slot)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': True, 'puzzle_id': puzzle.id, 'puzzle_number': puzzle.id})