import json
import requests

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
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
from .models import ConnectionsPuzzle, ConnectionsGroup, ConnectionsBookEntry, ConnectionsDraft


# ── Constants ─────────────────────────────────────────────────────────────────

DIFFICULTY_LEVELS = [
    {'order': 0, 'difficulty': 1, 'name': 'Easy',   'color': '#e8c84a'},
    {'order': 1, 'difficulty': 2, 'name': 'Medium',  'color': '#6aaa64'},
    {'order': 2, 'difficulty': 3, 'name': 'Hard',    'color': '#4a90d9'},
    {'order': 3, 'difficulty': 4, 'name': 'Expert',  'color': '#9b59b6'},
]


# ── Utility ───────────────────────────────────────────────────────────────────

def _get_or_fetch_book(google_book_id):
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


# ── Pages ─────────────────────────────────────────────────────────────────────

@login_required
def dashboard_home(request):
    from django.db.models import Count, Avg, Q
    from django.utils import timezone
    from datetime import timedelta
    from .models import PuzzleCompletion

    puzzles_qs = ConnectionsPuzzle.objects.select_related('created_by').order_by('-id')[:50]
    drafts     = ConnectionsDraft.objects.filter(created_by=request.user).order_by('-updated_at')

    # Attach stats to each puzzle
    one_week_ago = timezone.now() - timedelta(days=7)
    puzzle_list  = list(puzzles_qs)
    puzzle_ids   = [p.id for p in puzzle_list]

    # Aggregate all at once to avoid N+1 queries
    stats = (
        PuzzleCompletion.objects
        .filter(puzzle_id__in=puzzle_ids)
        .values('puzzle_id')
        .annotate(
            total_plays=Count('id'),
            wins=Count('id', filter=Q(won=True)),
            avg_mistakes=Avg('mistakes_made'),
            plays_this_week=Count('id', filter=Q(completed_at__gte=one_week_ago)),
        )
    )
    stats_map = {s['puzzle_id']: s for s in stats}

    for puzzle in puzzle_list:
        s = stats_map.get(puzzle.id, {})
        total = s.get('total_plays', 0)
        wins  = s.get('wins', 0)
        puzzle._stats = {
            'plays':         total,
            'win_rate':      f"{round(wins / total * 100)}%" if total else '—',
            'avg_mistakes':  f"{round(s['avg_mistakes'], 1)}" if s.get('avg_mistakes') is not None else '—',
            'plays_this_week': s.get('plays_this_week', 0),
        }

    context = {
        'puzzles': puzzle_list,
        'drafts':  drafts,
    }
    return render(request, 'dashboard/home.html', context)


@login_required
def create_connections(request):
    """Always starts a fresh blank editor."""
    context = {
        'draft_id':          None,
        'draft_data_json':   'null',
        'difficulty_levels': DIFFICULTY_LEVELS,
        'book_search_url':   '/api/book-search/',
    }
    return render(request, 'dashboard/create_connections.html', context)


@login_required
def edit_connections(request, draft_id):
    """Load an existing draft into the editor."""
    draft = get_object_or_404(ConnectionsDraft, pk=draft_id, created_by=request.user)
    context = {
        'draft_id':          draft.id,
        'draft_data_json':   json.dumps(draft.data),
        'difficulty_levels': DIFFICULTY_LEVELS,
        'book_search_url':   '/api/book-search/',
    }
    return render(request, 'dashboard/create_connections.html', context)


# ── Draft API ─────────────────────────────────────────────────────────────────

@login_required
@require_POST
def save_draft(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON.'}, status=400)

    draft_id   = data.get('draft_id')
    draft_data = data.get('data', {})

    if draft_id:
        # Update existing draft (must belong to this user)
        draft = get_object_or_404(ConnectionsDraft, pk=draft_id, created_by=request.user)
        draft.data = draft_data
        draft.save()
    else:
        # Create new draft
        draft = ConnectionsDraft.objects.create(
            created_by=request.user,
            data=draft_data,
        )

    return JsonResponse({'success': True, 'draft_id': draft.id})


@login_required
@require_POST
def delete_draft(request, draft_id):
    draft = get_object_or_404(ConnectionsDraft, pk=draft_id, created_by=request.user)
    draft.delete()
    return JsonResponse({'success': True})



# ── Edit published puzzle ─────────────────────────────────────────────────────

@login_required
def edit_puzzle(request, puzzle_id):
    puzzle = get_object_or_404(ConnectionsPuzzle, pk=puzzle_id)

    groups = []
    for group in puzzle.groups.prefetch_related('books__book__author'):
        books = []
        for entry in group.books.all():
            b = entry.book
            cover = (b.thumbnail_url or '').replace('http://', 'https://')
            books.append({
                'id':     b.google_book_id,
                'title':  b.title,
                'author': b.author.name if b.author else 'Unknown',
                'cover':  cover,
            })
        groups.append({'category': group.category, 'books': books})

    all_ids = list(ConnectionsPuzzle.objects.order_by('id').values_list('id', flat=True))
    rank    = (all_ids.index(puzzle_id) + 1) if puzzle_id in all_ids else puzzle_id

    context = {
        'draft_id':          None,
        'draft_data_json':   json.dumps({'groups': groups}),
        'difficulty_levels': DIFFICULTY_LEVELS,
        'book_search_url':   '/api/book-search/',
        'edit_puzzle_id':    puzzle_id,
        'edit_puzzle_rank':  rank,
    }
    return render(request, 'dashboard/create_connections.html', context)


@login_required
@require_POST
def update_connections_puzzle(request, puzzle_id):
    puzzle = get_object_or_404(ConnectionsPuzzle, pk=puzzle_id)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON.'}, status=400)

    groups_data = data.get('groups', [])

    if len(groups_data) != 4:
        return JsonResponse({'success': False, 'error': 'Puzzle must have exactly 4 groups.'}, status=400)

    for i, g in enumerate(groups_data, start=1):
        if not g.get('category', '').strip():
            return JsonResponse({'success': False, 'error': f'Group {i} is missing a category name.'}, status=400)
        if len(g.get('books', [])) != 4 or any(b is None for b in g['books']):
            return JsonResponse({'success': False, 'error': f'Group {i} must have exactly 4 books.'}, status=400)

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
            puzzle.groups.all().delete()
            for order, (group_data, books) in enumerate(zip(groups_data, resolved)):
                group = ConnectionsGroup.objects.create(
                    puzzle=puzzle,
                    category=group_data['category'].strip(),
                    difficulty=order + 1,
                    order=order,
                )
                for slot, (book_data, book) in enumerate(zip(group_data['books'], books)):
                    ConnectionsBookEntry.objects.create(group=group, book=book, slot=slot)
                    override = (book_data.get('cover_override') or '').strip()
                    if override and override != book.thumbnail_url:
                        Book.objects.filter(pk=book.pk).update(thumbnail_url=override)
            puzzle.save()
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': True, 'puzzle_id': puzzle.id})


# ── Puzzle save ───────────────────────────────────────────────────────────────

@login_required
@require_POST
def save_connections_puzzle(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON.'}, status=400)

    groups_data = data.get('groups', [])
    draft_id    = data.get('draft_id')

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

    # Ensure all 16 books are in the DB
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
                for slot, (book_data, book) in enumerate(zip(group_data['books'], books)):
                    ConnectionsBookEntry.objects.create(group=group, book=book, slot=slot)
                    # Apply cover override if the editor set one
                    override = (book_data.get('cover_override') or '').strip()
                    if override and override != book.thumbnail_url:
                        Book.objects.filter(pk=book.pk).update(thumbnail_url=override)

            # Delete the draft now that it's been published
            if draft_id:
                ConnectionsDraft.objects.filter(pk=draft_id, created_by=request.user).delete()

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': True, 'puzzle_id': puzzle.id, 'puzzle_number': puzzle.id})