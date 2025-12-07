from django.db import models

# Create your models here.

from django.db import models

class Author(models.Model):
    """
    Stores author information, simplified to fields retrievable from Google Books
    (or managed locally, like debut_novel).
    """
    name = models.CharField(max_length=500)
    
    # Links to the author's first published book (for debut novel category)
    debut_novel = models.ForeignKey(
        'Book',
        on_delete=models.SET_NULL,
        related_name='+', 
        null=True, 
        blank=True
    )

    def __str__(self):
        return self.name

class Subject(models.Model):
    """
    Stores canonical subject categories (e.g., 'Fiction', 'History', 'War').
    These map directly to Google Books' categories.
    """
    name = models.CharField(max_length=500, unique=True)

    def __str__(self):
        return self.name

class Book(models.Model):
    """
    Stores cached book data. The 'google_book_id' is used as the primary key
    for fast lookups and preventing duplicates from the API.
    """
    # Unique identifier from the Google Books API (used as Primary Key for cache)
    google_book_id = models.CharField(max_length=100, primary_key=True, default="temp-id")
    
    title = models.CharField(max_length=500)
    
    # Link to the Author model
    author = models.ForeignKey(Author, on_delete=models.CASCADE, null=True, related_name="books")
    
    # Book metadata from API
    publish_year = models.IntegerField(null=True, blank=True)
    page_count = models.IntegerField(null=True, blank=True)
    thumbnail_url = models.URLField(max_length=500, null=True, blank=True)
    isbn = models.CharField(max_length=13, null=True, blank=True) 

    # Link to Subject model (for War, Historical Fiction categories)
    subjects = models.ManyToManyField(Subject, related_name="books")
    
    def __str__(self):
        return f"{self.title}"

    class Meta:
        verbose_name_plural = "Books"