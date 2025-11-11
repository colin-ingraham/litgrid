from django.db import models

# Create your models here.



class Author(models.Model):
    name = models.CharField(max_length=500)
    nationality = models.CharField(max_length=500, default="Unknown")
    debut_novel = models.ForeignKey(
        'Book',
        on_delete=models.SET_NULL, # If the book is deleted, clear this field.
        related_name='+',          # Tells Django not to create a reverse accessor on Book.
        null=True,                 # Necessary because you create the Author before the Book.
        blank=True
    )
    gender = models.CharField(max_length=1, default="U")
    key = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return f"{self.name}"

class Subject(models.Model):
    name = models.CharField(max_length = 500, unique=True)

    def __str__(self):
        return f"{self.name}"

class Book(models.Model):
    title = models.CharField(max_length=500)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, null=True, related_name="books")
    publish_year = models.IntegerField(null=True, blank=True)
    page_count = models.IntegerField(null=True, blank=True)
    subjects = models.ManyToManyField(Subject, related_name="books")
    region = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    city = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    fictional_world = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    is_nytbs = models.BooleanField(default=False, blank=True)
    is_banned = models.BooleanField(default=False, blank=True)

    key = models.CharField(max_length=20, unique=True)
    cover_id = models.IntegerField(null=True, blank=True)
    isbn = models.CharField(max_length=13, null=True, blank=True, unique=True) 

    def __str__(self):
        return f"{self.title}"

    

