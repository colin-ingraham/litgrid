from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class ConnectionsPuzzle(models.Model):
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    release_date = models.DateField(
        null=True, blank=True,
        help_text="Date this puzzle becomes available to players. Null = queued/unreleased."
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='connections_puzzles',
    )

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"Connections Puzzle #{self.id}"

    @property
    def number(self):
        return self.id

    @property
    def is_released(self):
        if not self.release_date:
            return False
        return self.release_date <= timezone.now().date()

    def is_complete(self):
        groups = self.groups.prefetch_related('books')
        return groups.count() == 4 and all(g.books.count() == 4 for g in groups)


class ConnectionsGroup(models.Model):
    DIFFICULTY_CHOICES = [(1, 'Easy'), (2, 'Medium'), (3, 'Hard'), (4, 'Expert')]
    DIFF_LABELS  = {1: 'Easy', 2: 'Medium', 3: 'Hard', 4: 'Expert'}
    DIFF_COLORS  = {1: '#e8c84a', 2: '#6aaa64', 3: '#4a90d9', 4: '#9b59b6'}

    puzzle     = models.ForeignKey(ConnectionsPuzzle, related_name='groups', on_delete=models.CASCADE)
    category   = models.CharField(max_length=200)
    difficulty = models.IntegerField(choices=DIFFICULTY_CHOICES)
    order      = models.IntegerField()

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Puzzle #{self.puzzle_id} | G{self.order + 1}: {self.category}"

    @property
    def color(self):
        return self.DIFF_COLORS.get(self.difficulty, '#888888')

    @property
    def label(self):
        return self.DIFF_LABELS.get(self.difficulty, '')


class ConnectionsBookEntry(models.Model):
    group = models.ForeignKey(ConnectionsGroup, related_name='books', on_delete=models.CASCADE)
    book  = models.ForeignKey('library.Book', on_delete=models.PROTECT)
    slot  = models.IntegerField()

    class Meta:
        ordering = ['slot']
        unique_together = [('group', 'slot'), ('group', 'book')]

    def __str__(self):
        return f"{self.group} | Slot {self.slot}: {self.book.title}"


class PuzzleCompletion(models.Model):
    """
    One row per finished game (won or lost).
    session_key is Django's anonymous session identifier — no PII stored.
    Unique on (puzzle, session_key) so replaying doesn't inflate counts.
    """
    puzzle        = models.ForeignKey(
        ConnectionsPuzzle, on_delete=models.CASCADE,
        related_name='completions',
    )
    session_key   = models.CharField(max_length=40, db_index=True)
    won           = models.BooleanField()
    mistakes_made = models.IntegerField(default=0)   # 0–4
    completed_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('puzzle', 'session_key')]
        ordering = ['-completed_at']

    def __str__(self):
        result = 'Won' if self.won else 'Lost'
        return f"Puzzle #{self.puzzle_id} — {result} ({self.completed_at:%Y-%m-%d})"


class ConnectionsDraft(models.Model):
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='connections_drafts',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    data       = models.JSONField(default=dict)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Draft #{self.id} by {self.created_by} ({self.updated_at:%Y-%m-%d %H:%M})"

    def books_placed(self):
        try:
            return sum(
                1 for g in self.data.get('groups', [])
                for b in g.get('books', [])
                if b is not None
            )
        except Exception:
            return 0

    def preview_title(self):
        try:
            for g in self.data.get('groups', []):
                if g.get('category', '').strip():
                    return g['category'].strip()
        except Exception:
            pass
        return 'Untitled Draft'