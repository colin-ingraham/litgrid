from django.db import models

# Create your models here.

class Author(models.Model):
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=30)
    name = models.CharField(max_length=200)
    key = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.name}"

class Subject(models.Model):
    name = models.CharField(max_length = 200)

    def __str__(self):
        return f"{self.name}"

class Book(models.Model):
    title = models.CharField(max_length=50)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, null=True)
    publish_year = models.IntegerField()
    page_count = models.IntegerField()
    subjects = models.ManyToManyField(Subject)
    key = models.CharField(max_length=20)
    cover_id = models.IntegerField()
    isbn = models.CharField(max_length=13, null=True, blank=True) 

    def __str__(self):
        return f"{self.title}"

    

