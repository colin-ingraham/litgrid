import json
import requests
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings

GOOGLE_BOOKS_URL    = "https://www.googleapis.com/books/v1/volumes"
PLACEHOLDER_COVER   = 'https://placehold.co/60x90/2D2D2D/C9A86A?text=N%2FA'
SESSION_COMPLETE    = 'connections_completed'   # {str(puzzle_id): {guessHistory, mistakes, won}}
SESSION_PROGRESS    = 'connections_progress'    # {str(puzzle_id): {solvedGroups, playerSolvedGroups, guessHistory, mistakes}}


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
    completed_map = request.session.get(SESSION_COMPLETE, {})
    progress_map  = request.session.get(SESSION_PROGRESS, {})
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
            prior    = completed_map.get(str(current_id))   # fully done
            progress = progress_map.get(str(current_id))    # mid-game
        else:
            puzzle_data  = None
            current_id   = None
            current_rank = None
            prior        = None
            progress     = None

    except Exception:
        puzzle_data  = None
        current_id   = None
        current_rank = None
        all_puzzles  = []
        prior        = None
        progress     = None

    context = {
        'puzzle_data_json':    json.dumps(puzzle_data) if puzzle_data else 'null',
        'current_puzzle_id':   current_id,
        'current_rank':        current_rank,
        'all_puzzles_json':    json.dumps(all_puzzles),
        'prior_result_json':   json.dumps(prior)    if prior    else 'null',
        'progress_result_json': json.dumps(progress) if progress else 'null',
        'complete_url':        f'/connections/api/complete/{current_id}/'  if current_id else '',
        'progress_url':        f'/connections/api/progress/{current_id}/'  if current_id else '',
    }
    return render(request, 'connections/connections.html', context)


@require_POST
def save_completion(request, puzzle_id):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON.'}, status=400)

    # Write to completed
    completed_map = request.session.get(SESSION_COMPLETE, {})
    completed_map[str(puzzle_id)] = {
        'guessHistory': data.get('guessHistory', []),
        'mistakes':     data.get('mistakes', 0),
        'won':          data.get('won', False),
    }
    request.session[SESSION_COMPLETE] = completed_map

    # Clear in-progress entry — no longer needed
    progress_map = request.session.get(SESSION_PROGRESS, {})
    progress_map.pop(str(puzzle_id), None)
    request.session[SESSION_PROGRESS] = progress_map

    request.session.modified = True
    return JsonResponse({'success': True})


@require_POST
def save_progress(request, puzzle_id):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON.'}, status=400)

    progress_map = request.session.get(SESSION_PROGRESS, {})
    progress_map[str(puzzle_id)] = {
        'solvedGroups':       data.get('solvedGroups', []),
        'playerSolvedGroups': data.get('playerSolvedGroups', []),
        'guessHistory':       data.get('guessHistory', []),
        'mistakes':           data.get('mistakes', 4),
    }
    request.session[SESSION_PROGRESS] = progress_map
    request.session.modified = True
    return JsonResponse({'success': True})