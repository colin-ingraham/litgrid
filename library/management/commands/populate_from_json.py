from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import requests
import json
import time
from library.models import Author, Book, Subject


class Command(BaseCommand):
    help = "Populates the database with authors and books from a JSON file, fetching additional data from OpenLibrary API."

    def add_arguments(self, parser):
        parser.add_argument(
            'json_file',
            type=str,
            help="Path to the JSON file containing author and book data."
        )

    def handle(self, *args, **options):
        json_file = options['json_file']
        
        # Set User-Agent header for API requests
        self.headers = {
            'User-Agent': 'Litgrid/1.0 (https://github.com/colin-ingraham/litgrid; colinringraham@email.com)'
        }
        
        try:
            # Load JSON data
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.stdout.write(self.style.SUCCESS(f"Loaded JSON file: {json_file}"))
            self.stdout.write(f"Processing {len(data)} authors...")
            
            # Process each author
            for author_data in data:
                self.process_author(author_data)
                
            self.stdout.write(self.style.SUCCESS("✓ Database population complete!"))
            
        except FileNotFoundError:
            raise CommandError(f"File not found: {json_file}")
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON format: {e}")
        except Exception as e:
            raise CommandError(f"Error processing data: {e}")

    def process_author(self, author_data):
        """Process a single author and all their books"""
        author_name = author_data.get('author_name')
        author_key = author_data.get('author_key')
        nationality = author_data.get('nationality', 'Unknown')
        gender = author_data.get('gender', 'U')
        
        self.stdout.write(f"\nProcessing author: {author_name}")
        
        # Create or get the author
        author, created = Author.objects.get_or_create(
            key=author_key,
            defaults={
                'name': author_name,
                'nationality': nationality,
                'gender': gender,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f"  ✓ Created author: {author_name}"))
        else:
            # Update existing author
            author.name = author_name
            author.nationality = nationality
            author.gender = gender
            author.save()
            self.stdout.write(f"  → Updated author: {author_name}")
        
        # Process books
        books_data = author_data.get('books', [])
        debut_book = None
        
        for book_data in books_data:
            book = self.process_book(book_data, author)
            
            # Track debut novel
            if book_data.get('is_debut', False):
                debut_book = book
        
        # Set debut novel if found
        if debut_book and author.debut_novel != debut_book:
            author.debut_novel = debut_book
            author.save()
            self.stdout.write(f"  ✓ Set debut novel: {debut_book.title}")

    def process_book(self, book_data, author):
        """Process a single book and fetch additional data from API"""
        title = book_data.get('title')
        book_key = book_data.get('key')
        publish_year = book_data.get('publish_year')
        page_count = book_data.get('page_count')
        subjects_list = book_data.get('subjects', [])
        
        self.stdout.write(f"  → Processing book: {title}")
        
        # Fetch additional data from OpenLibrary if we have a work key
        cover_id = None
        isbn = None
        
        if book_key:
            api_data = self.fetch_openlibrary_data(book_key)
            cover_id = api_data.get('cover_id')
            isbn = api_data.get('isbn')
            
            # If page_count is missing from JSON, try to get it from API
            if page_count is None or page_count == -1:
                page_count = api_data.get('page_count')
        
        # Create or update the book
        book, created = Book.objects.update_or_create(
            key=book_key,
            defaults={
                'title': title,
                'author': author,
                'publish_year': publish_year,
                'page_count': page_count,
                'cover_id': cover_id,
                'isbn': isbn,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f"    ✓ Created book: {title}"))
        else:
            self.stdout.write(f"    → Updated book: {title}")
        
        # Process subjects
        if subjects_list:
            self.process_subjects(book, subjects_list)
        
        return book

    def fetch_openlibrary_data(self, work_key):
        """Fetch cover_id, isbn, and page_count from OpenLibrary API"""
        try:
            # Fetch work details to get editions
            work_url = f"https://openlibrary.org{work_key}.json"
            
            # Add a small delay to avoid rate limiting
            time.sleep(0.2)
            
            response = requests.get(work_url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                self.stdout.write(self.style.WARNING(f"    ⚠ API returned status {response.status_code} for {work_key}"))
                return {}
            
            work_data = response.json()
            
            # Try to get cover from work level first (some works have covers)
            cover_id = None
            if 'covers' in work_data and work_data['covers']:
                cover_id = work_data['covers'][0]
            
            # If no cover at work level, fetch the work's editions to find one with a cover
            if not cover_id:
                editions_url = f"https://openlibrary.org{work_key}/editions.json"
                time.sleep(0.2)
                
                editions_response = requests.get(editions_url, headers=self.headers, timeout=10)
                
                if editions_response.status_code == 200:
                    editions_data = editions_response.json()
                    entries = editions_data.get('entries', [])
                    
                    # Find the first edition with a cover
                    for edition in entries:
                        if 'covers' in edition and edition['covers']:
                            cover_id = edition['covers'][0]
                            break
            
            # Try to get ISBN and page count from editions
            isbn = None
            page_count = None
            
            # Fetch editions if we haven't already
            if not cover_id or not isbn or not page_count:
                editions_url = f"https://openlibrary.org{work_key}/editions.json"
                time.sleep(0.2)
                
                editions_response = requests.get(editions_url, headers=self.headers, timeout=10)
                
                if editions_response.status_code == 200:
                    editions_data = editions_response.json()
                    entries = editions_data.get('entries', [])
                    
                    # Find the first edition with the data we need
                    for edition in entries:
                        # Get cover if we don't have one yet
                        if not cover_id and 'covers' in edition and edition['covers']:
                            cover_id = edition['covers'][0]
                        
                        # Get ISBN if we don't have one yet
                        if not isbn:
                            if 'isbn_13' in edition and edition['isbn_13']:
                                isbn = edition['isbn_13'][0]
                            elif 'isbn_10' in edition and edition['isbn_10']:
                                isbn = edition['isbn_10'][0]
                        
                        # Get page count if we don't have one yet
                        if not page_count and 'number_of_pages' in edition:
                            page_count = edition['number_of_pages']
                        
                        # Break if we have everything
                        if cover_id and isbn and page_count:
                            break
            
            return {
                'cover_id': cover_id,
                'isbn': isbn,
                'page_count': page_count,
            }
            
        except requests.exceptions.Timeout:
            self.stdout.write(self.style.WARNING(f"    ⚠ API timeout for {work_key}"))
            return {}
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.WARNING(f"    ⚠ API error for {work_key}: {e}"))
            return {}
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"    ⚠ Error parsing API response for {work_key}: {e}"))
            return {}

    def process_subjects(self, book, subjects_list):
        """Create or get subjects and link them to the book"""
        # Clear existing subjects
        book.subjects.clear()
        
        for subject_name in subjects_list:
            # Normalize subject name (lowercase, strip whitespace)
            subject_name = subject_name.strip().lower()
            
            # Create or get subject
            subject, created = Subject.objects.get_or_create(
                name=subject_name
            )
            
            # Link to book
            book.subjects.add(subject)
        
        if subjects_list:
            self.stdout.write(f"    ✓ Linked {len(subjects_list)} subjects")