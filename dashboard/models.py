from django.db import models
from django.contrib.auth.models import User


class ConnectionsPuzzle(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='connections_puzzles',
    )

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"Connections Puzzle #{self.id}"

    @property
    def number(self):
        return self.id

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
    order      = models.IntegerField()  # 0-3, locked during creation

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
    slot  = models.IntegerField()  # 0-3

    class Meta:
        ordering = ['slot']
        unique_together = [('group', 'slot'), ('group', 'book')]

    def __str__(self):
        return f"{self.group} | Slot {self.slot}: {self.book.title}"