from django.core.management.base import BaseCommand, CommandError
import requests

class Command(BaseCommand):
    help = "Fetches and structures data for a single book from OpenLibrary."

    def add_arguments(self, parser):
        parser.add_argument(
            'title',
            type=str,
            help="The title of the book being queried for."
        )

    def handle(self, *args, **options):
        title = options['title']
        
        # --- 1. Initialize all variables with safe defaults ---
        author_key = 'N/A'
        author_name = 'Unknown Author'
        author_first = 'Unknown'
        author_last = 'Author'
        publish_year = None
        book_key = None
        cover_id = 0
        page_count = -1
        isbn = None
        clean_subjects = []
        
        try:
            # --- 2. Initial Search (OpenLibrary Work) ---
            url = f"https://openlibrary.org/search.json?q={title}"
            response = requests.get(url, timeout=10).json()
            documents = response.get('docs', [])

            if not documents:
                # If no book is found, raise a clean error
                raise CommandError(f"No results found for title: {title}")
                
            result = documents[0]
            
            # --- Safely extract primary book data ---
            author_names = result.get('author_name', [])
            author_name = author_names[0] if author_names else 'Unknown Author'
            
            # Handle author name split defensively (in case it's just one word)
            name_parts = author_name.split(" ")
            author_first = name_parts[0]
            author_last = name_parts[-1] if len(name_parts) > 1 else ''
            
            author_keys = result.get('author_key', ['N/A'])
            author_key = author_keys[0]

            publish_year = result.get('first_publish_year', None)
            title = result.get('title', title)
            book_key = result.get('key')
            cover_id = result.get("cover_i", 0)

            # --- 3. Second API Call (Full Work Details) ---
            if book_key:
                second_url = f"https://openlibrary.org{book_key}.json"
                second_response = requests.get(second_url, timeout=10).json()

                page_count = second_response.get('number_of_pages', -1)
                subjects = second_response.get('subjects', [])

                isbn_list = second_response.get('isbn_13', [])
                isbn = isbn_list[0] if isbn_list else None
                
                # --- Process Subjects (as before) ---
                if subjects:
                    # Deduplication and normalization
                    normalized_subjects = [s.strip().lower() for s in subjects]
                    unique_subjects = set(normalized_subjects)
                    clean_subjects = list(unique_subjects)

            # --- 4. Return Structured Dictionary ---
            author_data = {
                'key': author_key,
                'first_name': author_first,
                'last_name': author_last,
                'name': author_name,
            }
            
            book_data = {
                'key': book_key,
                'title': title,
                'publish_year': publish_year,
                'cover_id': cover_id,
                'page_count': page_count,
                'isbn': isbn,
                'subjects': clean_subjects,
                'author_data': author_data,
            }
            return book_data

        except requests.exceptions.Timeout:
            raise CommandError(f"API Request timed out for: {title}")
        except Exception as e:
            # Catch any other specific errors
            raise CommandError(f'Error processing "{title}": {e}')