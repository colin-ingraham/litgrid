from django.core.management.base import BaseCommand
from game.views import validate_cell_to_category
from library.models import Book 

class Command(BaseCommand):
    help = 'Takes subject code input and calls validate cell on it using the first book in the DB.'

    def add_arguments(self, parser):
        # This tells Django to expect one argument called 'subject_code'
        parser.add_argument('subject_code', type=str, help='The logic code to test (e.g., SFantasy)')

    def handle(self, *args, **kwargs):
        # 1. Get the input code from kwargs (not args)
        code = kwargs['subject_code']
        
        # 2. Get a book to test against
        book = Book.objects.first()

        if not book:
            self.stdout.write(self.style.ERROR("No books found in database to test against."))
            return

        self.stdout.write(f"Testing Subject Code: '{code}' against Book: '{book.title}'...")

        # 3. Run validation
        # (Ensure validate_cell_to_category expects a string code, not a Category object)
        valid = validate_cell_to_category(code, book)
        
        # 4. Output result
        if valid:
            self.stdout.write(self.style.SUCCESS(f"RESULT: True (Match)"))
        else:
            self.stdout.write(self.style.ERROR(f"RESULT: False (No Match)"))