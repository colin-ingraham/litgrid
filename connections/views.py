import json
import requests
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings

GOOGLE_BOOKS_URL  = "https://www.googleapis.com/books/v1/volumes"
PLACEHOLDER_COVER = 'https://placehold.co/60x90/2D2D2D/C9A86A?text=N%2FA'
SESSION_KEY       = 'connections_completed'  # { str(puzzle_id): { guessHistory, mistakes, won } }


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
    groups = []
    for group in puzzle.groups.prefetch_related('books__book__author'):
        books = []
        for entry in group.books.all():
            b     = entry.book
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


def _all_puzzle_stubs(completed_ids):
    try:
        from dashboard.models import ConnectionsPuzzle
        ids = list(
            ConnectionsPuzzle.objects
            .order_by('id')
            .values_list('id', flat=True)
        )
        return [
            {
                'id':        pid,
                'rank':      rank,
                'completed': pid in completed_ids,
            }
            for rank, pid in enumerate(ids, start=1)
        ]
    except Exception:
        return []


def ConnectionsGame(request, puzzle_id=None):
    # Read completed puzzles from session
    completed_map = request.session.get(SESSION_KEY, {})
    completed_ids = {int(k) for k in completed_map.keys()}

    try:
        from dashboard.models import ConnectionsPuzzle

        all_puzzles = _all_puzzle_stubs(completed_ids)

        if puzzle_id is not None:
            puzzle = get_object_or_404(ConnectionsPuzzle, pk=puzzle_id)
        else:
            puzzle = ConnectionsPuzzle.objects.order_by('id').first()

        if puzzle:
            puzzle_data  = _puzzle_to_json(puzzle)
            current_id   = puzzle.id
            current_rank = next(
                (p['rank'] for p in all_puzzles if p['id'] == current_id), 1
            )
            # Prior completion data for this puzzle (if any)
            prior = completed_map.get(str(current_id))
        else:
            puzzle_data  = None
            current_id   = None
            current_rank = None
            prior        = None

    except Exception:
        puzzle_data  = None
        current_id   = None
        current_rank = None
        all_puzzles  = []
        prior        = None

    context = {
        'puzzle_data_json':   json.dumps(puzzle_data) if puzzle_data else 'null',
        'current_puzzle_id':  current_id,
        'current_rank':       current_rank,
        'all_puzzles_json':   json.dumps(all_puzzles),
        'prior_result_json':  json.dumps(prior) if prior else 'null',
        'complete_url':       f'/connections/api/complete/{current_id}/' if current_id else '',
    }
    return render(request, 'connections/connections.html', context)


@require_POST
def save_completion(request, puzzle_id):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON.'}, status=400)

    completed_map = request.session.get(SESSION_KEY, {})
    completed_map[str(puzzle_id)] = {
        'guessHistory': data.get('guessHistory', []),
        'mistakes':     data.get('mistakes', 0),
        'won':          data.get('won', False),
    }
    request.session[SESSION_KEY] = completed_map
    request.session.modified     = True
    return JsonResponse({'success': True})