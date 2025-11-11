from django.core.management.base import BaseCommand
from library.models import Book

class Command(BaseCommand):
    help = "Lists all books currently in the database with their details for cleaning review."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("--- Current Books in Database ---"))
        
        books = Book.objects.select_related('author').prefetch_related('subjects').all()
        
        if not books:
            self.stdout.write(self.style.WARNING("The database contains no books."))
            return

        for book in books:
            
            # Print details in a clear block format
            self.stdout.write("-" * 50)
            self.stdout.write(self.style.SUCCESS(f"TITLE: {book.title}"))
            self.stdout.write(f"AUTHOR: {book.author.name if book.author else 'N/A'}")
        
        self.stdout.write("-" * 50)
        self.stdout.write(self.style.SUCCESS(f"Total Books: {books.count()}"))