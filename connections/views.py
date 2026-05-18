from django.shortcuts import render
import json
import requests
from datetime import date
from django.conf import settings

GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
PLACEHOLDER_COVER = 'https://placehold.co/60x90/2D2D2D/C9A86A?text=N%2FA'


def _fetch_cover_from_api(title, author):
    """
    Hits Google Books API for a single book cover.
    Returns an https thumbnail URL, or '' on failure.
    """
    api_key = getattr(settings, 'GOOGLE_BOOKS_API_KEY', '')
    params = {
        'q': f'intitle:{title} inauthor:{author}',
        'maxResults': 3,
        'key': api_key,
        'fields': 'items(volumeInfo(title,authors,imageLinks))',
    }
    try:
        resp = requests.get(GOOGLE_BOOKS_URL, params=params, timeout=5)
        resp.raise_for_status()
        for item in resp.json().get('items', []):
            links = item.get('volumeInfo', {}).get('imageLinks', {})
            thumb = links.get('thumbnail') or links.get('smallThumbnail')
            if thumb:
                # Google Books still serves HTTP URLs — upgrade them
                return thumb.replace('http://', 'https://')
    except Exception:
        pass
    return ''


def _enrich_books(groups):
    """
    Mutates each book dict in-place, adding a 'cover' key.

    Priority:
      1. Book.thumbnail_url from the local DB (fast, no API call)
      2. Google Books API search (slow, only when DB misses)
      3. Placeholder image
    """
    # Gracefully skip if the library app isn't installed / migrated yet
    try:
        from library.models import Book as LibraryBook
    except Exception:
        LibraryBook = None

    for group in groups:
        for book in group['books']:
            cover = ''

            # --- 1. DB lookup ---
            if LibraryBook is not None:
                try:
                    db_book = (
                        LibraryBook.objects
                        .filter(title__iexact=book['title'])
                        .select_related('author')
                        .first()
                    )
                    if db_book and db_book.thumbnail_url:
                        cover = db_book.thumbnail_url.replace('http://', 'https://')
                except Exception:
                    pass

            # --- 2. API fallback ---
            if not cover:
                cover = _fetch_cover_from_api(book['title'], book['author'])

            # --- 3. Placeholder ---
            book['cover'] = cover or PLACEHOLDER_COVER

    return groups


def ConnectionsGame(request):
    sample_puzzle = {
        'groups': [
            {
                'category': 'One-Word Titles',
                'difficulty': 1,
                'books': [
                    {'title': 'Beloved', 'author': 'Toni Morrison'},
                    {'title': 'Dune', 'author': 'Frank Herbert'},
                    {'title': 'Frankenstein', 'author': 'Mary Shelley'},
                    {'title': 'Lolita', 'author': 'Vladimir Nabokov'},
                ],
            },
            {
                'category': 'Set in a Dystopian Future',
                'difficulty': 2,
                'books': [
                    {'title': '1984', 'author': 'George Orwell'},
                    {'title': 'Brave New World', 'author': 'Aldous Huxley'},
                    {'title': "The Handmaid's Tale", 'author': 'Margaret Atwood'},
                    {'title': 'Fahrenheit 451', 'author': 'Ray Bradbury'},
                ],
            },
            {
                'category': 'Written by a Brontë',
                'difficulty': 3,
                'books': [
                    {'title': 'Jane Eyre', 'author': 'Charlotte Brontë'},
                    {'title': 'Wuthering Heights', 'author': 'Emily Brontë'},
                    {'title': 'The Tenant of Wildfell Hall', 'author': 'Anne Brontë'},
                    {'title': 'Agnes Grey', 'author': 'Anne Brontë'},
                ],
            },
            {
                'category': 'Color in the Title',
                'difficulty': 4,
                'books': [
                    {'title': 'The Color Purple', 'author': 'Alice Walker'},
                    {'title': 'The Scarlet Letter', 'author': 'Nathaniel Hawthorne'},
                    {'title': 'The Red Badge of Courage', 'author': 'Stephen Crane'},
                    {'title': 'Fifty Shades of Grey', 'author': 'E.L. James'},
                ],
            },
        ]
    }

    _enrich_books(sample_puzzle['groups'])

    context = {
        'puzzle_data_json': json.dumps(sample_puzzle),
        'puzzle_date': date.today().strftime('%Y-%m-%d'),
        'display_date': date.today().strftime('%B %d, %Y'),
    }
    return render(request, 'connections/connections.html', context)