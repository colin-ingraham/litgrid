from concurrent.futures import ThreadPoolExecutor, as_completed
from django.core.management import call_command
from django.core.management.base import BaseCommand
from library.models import Book, Author, Subject
from django.db import transaction
import time
from library.management.commands.fetch_book_data import Command as FetchCommand

MAX_WORKERS = 8

class Command(BaseCommand):
    help = "Takes list of Books, structured like ['Pride and Prejudice', 'Frankenstein', etc] and saves them all to the database."
    
    def add_arguments(self, parser):
        parser.add_argument(
            'book_titles',
            nargs='+',
            type=str,
            help="The list of books being added."
        )

    def execute_fetch_book(self, title):
        """Executes the fetch command's logic directly and returns the dict."""
        fetcher = FetchCommand()
        # Mock the options dictionary needed by the handle method
        options = {'title': title}
        # Call the handle method directly!
        return fetcher.handle(None, **options)

    def handle(self, *args, **options):
        book_titles = options["book_titles"]
        start_time = time.time()
        fetched_data = []

        self.stdout.write(self.style.NOTICE(f"Starting concurrent upload of {len(book_titles)} books with {MAX_WORKERS} workers..."))

        # --- 1. CONCURRENT FETCH (API Calls) ---
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(self.execute_fetch_book, title) 
                        for title in book_titles]
            
            for future in as_completed(futures):
                try:
                    data = future.result()
                    if data:
                        fetched_data.append(data)
                        self.stdout.write(f"Fetched data for: {data['title']}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"A fetch failed: {e}"))
        
         # --- 2. SEQUENTIAL BULK SAVE (Database Optimization) ---
        # Run all database writes within a single atomic block for integrity
        self.stdout.write(self.style.NOTICE("\n--- Starting Bulk Database Save ---"))
        with transaction.atomic():
            
            # 2a. Collect unique authors and subjects from all fetched books
            all_author_data = {d['author_data']['key']: d['author_data'] for d in fetched_data}
            all_subject_names = set()
            for d in fetched_data:
                all_subject_names.update(d['subjects'])
            
            # 2b. Bulk Create/Update Subjects
            for name in all_subject_names:
                Subject.objects.get_or_create(name=name)
            subject_map = {s.name: s for s in Subject.objects.filter(name__in=all_subject_names)}
            
            # 2c. Bulk Create/Update Authors (Iterate data to update/create one-by-one, but faster)
            author_map = {}
            for key, data in all_author_data.items():
                author_obj, _ = Author.objects.update_or_create(key=key, defaults=data)
                author_map[key] = author_obj
            
            # 2d. Create/Update Books and link relationships
            for data in fetched_data:
                author_obj = author_map[data['author_data']['key']]
                
                # Update the book defaults with the Author instance
                book_defaults = {k: v for k, v in data.items() if k not in ['key', 'subjects', 'author_data']}
                book_defaults['author'] = author_obj
                
                # Create/Update the book
                book_obj, _ = Book.objects.update_or_create(key=data['key'], defaults=book_defaults)
                
                # 2e. Bulk Link Subjects (Use a single set of transactions)
                subjects_to_link = [subject_map[name] for name in data['subjects'] if name in subject_map]
                book_obj.subjects.set(subjects_to_link) 
        
        self.stdout.write(self.style.SUCCESS("\nDatabase population complete!"))

        
        end_time = time.time()
        self.stdout.write(self.style.SUCCESS(f"\nAll tasks finished in {end_time - start_time:.2f} seconds."))
        