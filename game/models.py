from django.db import models

class Category(models.Model):
    """
    Represents a puzzle category (e.g., 'Sci-Fi', 'One Word Title').
    Used to dynamically generate daily grids.
    """
    # 1. The Actual Category Display Name (e.g., "Books under 200 pages")
    display_name = models.CharField(max_length=200, unique=True)

    # 2. The Subject Code used for backend logic mapping
    # We use a SlugField or CharField. This must match the 'case' in your validation.py
    # e.g., 'page_count_under_200', 'title_color', 'genre_fantasy'
    logic_code = models.CharField(
        max_length=100, 
        unique=True,
        help_text="This code must match the key in your validation logic (e.g., 'title_has_color')."
    )

    # 3. The Help Text (ToolTip)
    description = models.CharField(
        max_length=500, 
        blank=True, 
        help_text="Explanation that appears when user hovers/clicks (e.g., 'Must have fewer than 200 pages according to Google Books')."
    )

    # Utility fields
    is_active = models.BooleanField(default=True, help_text="Uncheck to hide this category from future puzzles.")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.display_name

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['display_name']
