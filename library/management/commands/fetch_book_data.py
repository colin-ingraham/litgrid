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

    def get_nationality(self, author_key, wikidata_id, headers):
        """Helper method to fetch nationality for an author"""
        try:
            # If no wikidata_id, can't fetch nationality
            if not wikidata_id:
                return "Unknown"
            
            # Query Wikidata
            wd_url = "https://www.wikidata.org/w/api.php"
            wd_params = {
                'action': 'wbgetentities',
                'ids': wikidata_id,
                'format': 'json',
                'props': 'claims'
            }
            
            wd_response = requests.get(wd_url, params=wd_params, headers=headers, timeout=10)
            
            if wd_response.status_code != 200:
                return "Unknown"
                
            wd_data = wd_response.json()
            
            # Extract nationality (P27 = country of citizenship)
            entity = wd_data['entities'][wikidata_id]
            claims = entity.get('claims', {})
            nationality_claims = claims.get('P27', [])
            
            if not nationality_claims:
                return "Unknown"
            
            # Get the first nationality ID
            nationality_id = nationality_claims[0]['mainsnak']['datavalue']['value']['id']
            
            # Get the country name
            country_params = {
                'action': 'wbgetentities',
                'ids': nationality_id,
                'format': 'json',
                'props': 'labels'
            }
            
            country_response = requests.get(wd_url, params=country_params, headers=headers, timeout=10)
            
            if country_response.status_code != 200:
                return "Unknown"
                
            country_data = country_response.json()
            country_name = country_data['entities'][nationality_id]['labels']['en']['value']
            
            return country_name
                
        except Exception:
            return "Unknown"

    def handle(self, *args, **options):
        title = options['title']
        
        # Set User-Agent header
        headers = {
            'User-Agent': 'Litgrid/1.0 (https://github.com/colin-ingraham/litgrid; colinringraham@email.com)'
        }
        
        # --- 1. Initialize all variables with safe defaults ---
        author_key = 'N/A'
        author_name = 'Unknown Author'
        author_first = 'Unknown'
        author_last = 'Author'
        nationality = 'Unknown'
        publish_year = None
        book_key = None
        cover_id = 0
        page_count = -1
        isbn = None
        clean_subjects = []
        
        try:
            # --- 2. Initial Search (OpenLibrary Work) ---
            url = f"https://openlibrary.org/search.json?q={title}"
            response = requests.get(url, headers=headers, timeout=10).json()
            documents = response.get('docs', [])

            if not documents:
                raise CommandError(f"No results found for title: {title}")
                
            result = documents[0]
            
            # --- Safely extract primary book data ---
            author_names = result.get('author_name', [])
            author_name = author_names[0] if author_names else 'Unknown Author'
            
            # Handle author name split defensively
            name_parts = author_name.split(" ")
            author_first = name_parts[0]
            author_last = name_parts[-1] if len(name_parts) > 1 else ''
            
            author_keys = result.get('author_key', ['N/A'])
            author_key = author_keys[0]

            publish_year = result.get('first_publish_year', None)
            title = result.get('title', title)
            book_key = result.get('key')
            cover_id = result.get("cover_i", 0)

            # --- 3. Get Author Details from OpenLibrary (for Wikidata ID) ---
            wikidata_id = None
            if author_key != 'N/A':
                try:
                    author_url = f"https://openlibrary.org/authors/{author_key}.json"
                    author_response = requests.get(author_url, headers=headers, timeout=10).json()
                    wikidata_id = author_response.get('remote_ids', {}).get('wikidata')
                except Exception:
                    pass  # If author fetch fails, continue without nationality
            
            # --- 4. Get Nationality ---
            if wikidata_id:
                nationality = self.get_nationality(author_key, wikidata_id, headers)

            # --- 5. Second API Call (Full Work Details) ---
            if book_key:
                second_url = f"https://openlibrary.org{book_key}.json"
                second_response = requests.get(second_url, headers=headers, timeout=10).json()

                page_count = second_response.get('number_of_pages', -1)
                subjects = second_response.get('subjects', [])

                isbn_list = second_response.get('isbn_13', [])
                isbn = isbn_list[0] if isbn_list else None
                
                # --- Process Subjects ---
                if subjects:
                    normalized_subjects = [s.strip().lower() for s in subjects]
                    unique_subjects = set(normalized_subjects)
                    clean_subjects = list(unique_subjects)

            # --- 6. Return Structured Dictionary ---
            author_data = {
                'key': author_key,
                'first_name': author_first,
                'last_name': author_last,
                'name': author_name,
                'nationality': nationality, 
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
            raise CommandError(f'Error processing "{title}": {e}')