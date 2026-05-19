import json
import requests
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.conf import settings

GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
PLACEHOLDER_COVER = 'https://placehold.co/60x90/2D2D2D/C9A86A?text=N%2FA'


def _fetch_cover_from_api(title, author):
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
                return thumb.replace('http://', 'https://')
    except Exception:
        pass
    return ''


def _puzzle_to_json(puzzle):
    """
    Convert a ConnectionsPuzzle ORM object into the dict shape the
    connections JS expects: { groups: [ { category, difficulty, books: [...] } ] }
    """
    groups = []
    for group in puzzle.groups.prefetch_related('books__book__author'):
        books = []
        for entry in group.books.all():
            b = entry.book
            thumb = (b.thumbnail_url or '').replace('http://', 'https://')
            if not thumb:
                thumb = _fetch_cover_from_api(b.title, b.author.name if b.author else '')
            books.append({
                'title':  b.title,
                'author': b.author.name if b.author else 'Unknown',
                'cover':  thumb or PLACEHOLDER_COVER,
            })
        groups.append({
            'category':   group.category,
            'difficulty': group.difficulty,
            'books':      books,
        })
    return {'groups': groups}


def _all_puzzle_stubs():
    """Return lightweight list of all puzzles for the selector."""
    try:
        from dashboard.models import ConnectionsPuzzle
        return list(
            ConnectionsPuzzle.objects
            .order_by('id')
            .values('id')
        )
    except Exception:
        return []


def ConnectionsGame(request, puzzle_id=None):
    try:
        from dashboard.models import ConnectionsPuzzle

        if puzzle_id is not None:
            puzzle = get_object_or_404(ConnectionsPuzzle, pk=puzzle_id)
        else:
            puzzle = ConnectionsPuzzle.objects.order_by('id').first()

        if puzzle:
            puzzle_data = _puzzle_to_json(puzzle)
            current_id  = puzzle.id
        else:
            puzzle_data = None
            current_id  = None

    except Exception:
        puzzle_data = None
        current_id  = None

    all_puzzles = _all_puzzle_stubs()

    context = {
        'puzzle_data_json': json.dumps(puzzle_data) if puzzle_data else 'null',
        'current_puzzle_id': current_id,
        'all_puzzles_json':  json.dumps(all_puzzles),
    }
    return render(request, 'connections/connections.html', context)