import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from library.models import Book, Author, Subject

# --- Configuration ---

MAX_WORKERS = 8  # Number of parallel threads to fetch data
HEADERS = {
    'User-Agent': 'Litgrid/2.0 (http://your-website.com; your-email@email.com)',
    'Accept': 'application/json'
}
OL_SEARCH_URL = "https://openlibrary.org/search.json"
OL_BASE_URL = "https://openlibrary.org"
WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"

# Cache for author details to avoid redundant API calls within a single run
AUTHOR_CACHE = {}

class Command(BaseCommand):
    help = ("Fetches and saves comprehensive data for a list of "
            "specific book titles.")

    def add_arguments(self, parser):
        parser.add_argument(
            'book_titles',
            nargs='+',
            type=str,
            help="The exact list of book titles to add."
        )

    def handle(self, *args, **options):
        """
        Main command handler. Orchestrates concurrent fetching and atomic saving.
        """
        book_titles = options["book_titles"]
        start_time = time.time()
        self.stdout.write(self.style.NOTICE(
            f"Starting concurrent ingestion for {len(book_titles)} books..."
        ))

        fetched_data_packages = []
        failed_titles = []

        # --- 1. CONCURRENT FETCHING (API CALLS) ---
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_title = {
                executor.submit(self.fetch_book_package, title): title
                for title in book_titles
            }

            for future in as_completed(future_to_title):
                title = future_to_title[future]
                try:
                    data = future.result()
                    if data:
                        fetched_data_packages.append(data)
                        self.stdout.write(self.style.SUCCESS(
                            f"Successfully fetched data for: {title}"
                        ))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f"Failed to process '{title}': {e}"
                    ))
                    failed_titles.append(title)

        self.stdout.write(self.style.NOTICE("\n--- API Fetching Complete ---"))
        if failed_titles:
            self.stdout.write(self.style.WARNING(
                f"Failed to fetch: {', '.join(failed_titles)}"
            ))

        # --- 2. SEQUENTIAL DATABASE SAVE (ATOMIC) ---
        self.stdout.write(self.style.NOTICE("--- Starting Bulk Database Save ---"))
        
        author_map = {}  # key: author_key, val: Author obj
        book_map = {}    # key: book_key, val: Book obj
        author_debut_map = {} # key: author_key, val: debut_book_key

        try:
            with transaction.atomic():
                # --- PASS 1: Create Subjects and Authors ---
                self.stdout.write("Pass 1: Creating Subjects and Authors...")
                all_subject_names = set()
                all_author_data = {}

                for pkg in fetched_data_packages:
                    all_author_data[pkg['author']['key']] = pkg['author']
                    all_subject_names.update(pkg['book']['subjects'])

                # Bulk get-or-create subjects
                subject_map = {}
                for name in all_subject_names:
                    subj, _ = Subject.objects.get_or_create(name=name)
                    subject_map[name] = subj

                # Create/Update Authors
                for author_key, data in all_author_data.items():
                    author_obj, created = Author.objects.update_or_create(
                        key=author_key,
                        defaults={
                            'name': data['name'],
                            'nationality': data['nationality'],
                            'gender': data['gender'],
                        }
                    )
                    author_map[author_key] = author_obj
                    author_debut_map[author_key] = data.get('debut_book_key')

                # --- PASS 2: Create Books and Link Subjects ---
                self.stdout.write("Pass 2: Creating Books...")
                for pkg in fetched_data_packages:
                    book_data = pkg['book']
                    author_obj = author_map.get(pkg['author']['key'])

                    if not author_obj:
                        self.stdout.write(self.style.WARNING(
                            f"Skipping book '{book_data['title']}', author not found."
                        ))
                        continue

                    book_obj, created = Book.objects.update_or_create(
                        key=book_data['key'],
                        defaults={
                            'title': book_data['title'],
                            'author': author_obj,
                            'publish_year': book_data.get('publish_year'),
                            'page_count': book_data.get('page_count'),
                            'cover_id': book_data.get('cover_id'),
                            'isbn': book_data.get('isbn'),
                            # Add other book fields here
                        }
                    )
                    book_map[book_obj.key] = book_obj

                    # Link subjects
                    subject_objs = [
                        subject_map[name] for name in book_data['subjects'] 
                        if name in subject_map
                    ]
                    book_obj.subjects.set(subject_objs)

                # --- PASS 3: Link Debut Novels ---
                self.stdout.write("Pass 3: Linking Debut Novels...")
                for author_key, debut_book_key in author_debut_map.items():
                    if debut_book_key and debut_book_key in book_map:
                        author_obj = author_map[author_key]
                        book_obj = book_map[debut_book_key]
                        if author_obj.debut_novel != book_obj:
                            author_obj.debut_novel = book_obj
                            author_obj.save()

        except Exception as e:
            raise CommandError(f"Database transaction failed: {e}")

        end_time = time.time()
        self.stdout.write(self.style.SUCCESS(
            f"\nDatabase ingestion complete! Total time: {end_time - start_time:.2f} seconds."
        ))

    # --- Main Fetching Function ---

    def fetch_book_package(self, title):
        """
        Fetches all data for a single, specific book title.
        This is the function run by each thread.
        """
        # --- 1. Find Best Book (Work) Match ---
        best_doc = self._find_best_book_match(title)
        if not best_doc:
            raise Exception("No matching English 'work' found.")

        book_key = best_doc.get('key')
        author_key = best_doc.get('author_key', [None])[0]
        
        if not book_key or not author_key:
            raise Exception("Work key or Author key is missing.")

        # --- 2. Get Detailed Book & Author Data (in parallel if possible) ---
        book_details = self._get_ol_book_details(book_key)
        
        # Use cache to avoid re-fetching author data
        if author_key in AUTHOR_CACHE:
            author_details = AUTHOR_CACHE[author_key]
        else:
            author_details = self._get_ol_author_details(author_key)
            AUTHOR_CACHE[author_key] = author_details

        # --- 3. Consolidate & Return Package ---
        book_data = {
            'key': book_key,
            'title': best_doc.get('title', title),
            'publish_year': best_doc.get('first_publish_year'),
            'cover_id': best_doc.get('cover_i'),
            'isbn': best_doc.get('isbn', [None])[0],
            'subjects': book_details.get('subjects', []),
            'page_count': book_details.get('page_count'),
            # Add other book fields here
        }
        
        return {
            'author': author_details,
            'book': book_data
        }

    # --- Private Helper Methods (API Calls) ---

    def _find_best_book_match(self, title):
        """Finds the best 'work' from OpenLibrary search."""
        params = {'title': title, 'language': 'eng', 'limit': 5}
        response = requests.get(OL_SEARCH_URL, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data['numFound'] == 0:
            return None
        
        docs = data.get('docs', [])
        
        #
        # --- DATA CLEANING ---
        #
        
        # Priority 1: Find an exact title match
        for doc in docs:
            if doc.get('title', '').lower() == title.lower() and doc.get('author_key'):
                return doc
                
        # Priority 2: Find the first result that is a "work" and has an author
        for doc in docs:
            if doc.get('key', '').startswith('/works/') and doc.get('author_key'):
                return doc
        
        return None # No good match found

    def _get_ol_book_details(self, book_key):
        """Gets detailed info (subjects, pages) for a specific /works/ key."""
        try:
            url = f"{OL_BASE_URL}{book_key}.json"
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # --- DATA CLEANING ---
            subjects_raw = data.get('subjects', [])
            # Filter out junk subjects like "places", "times", or long phrases
            subjects_clean = [
                s.strip().lower() for s in subjects_raw 
                if len(s) < 50 and "http" not in s and "times" not in s.lower()
            ]

            return {
                'subjects': list(set(subjects_clean)), # Remove duplicates
                'page_count': data.get('number_of_pages'),
            }
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"_get_ol_book_details error: {e}"))
            return {}

    def _get_ol_author_details(self, author_key):
        """Gets comprehensive data for a single author and finds their debut novel."""
        try:
            # --- 1. Get Author Details (Name, Wikidata ID) ---
            author_url = f"{OL_BASE_URL}/authors/{author_key}.json"
            author_response = requests.get(author_url, headers=HEADERS, timeout=10)
            author_response.raise_for_status()
            author_data = author_response.json()
            
            author_name = author_data.get('name', 'Unknown Author')
            wikidata_id = author_data.get('remote_ids', {}).get('wikidata')

            # --- 2. Get Wikidata Details (Gender, Nationality) ---
            gender, nationality = self._get_wikidata_details(wikidata_id)

            # --- 3. Find Debut Novel Key ---
            works_url = f"{OL_BASE_URL}/authors/{author_key}/works.json"
            works_params = {'limit': 200, 'sort': 'old'} # Sort by oldest
            works_response = requests.get(works_url, params=works_params, headers=HEADERS, timeout=10)
            works_response.raise_for_status()
            works_data = works_response.json()

            debut_book_key = None
            if works_data.get('entries'):
                # The first entry *should* be the oldest, but we double-check year
                earliest_year = 9999
                for entry in works_data['entries']:
                    year = entry.get('first_publish_year')
                    if year and year < earliest_year:
                        earliest_year = year
                        debut_book_key = entry.get('key')
                        
                # If no years found, just take the first one from 'old' sort
                if not debut_book_key:
                     debut_book_key = works_data['entries'][0].get('key')


            return {
                'key': author_key,
                'name': author_name,
                'gender': gender,
                'nationality': nationality,
                'debut_book_key': debut_book_key
            }

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"_get_ol_author_details error: {e}"))
            return {}

    def _get_wikidata_details(self, wikidata_id):
        """Fetches Nationality (P27) and Gender (P21) from Wikidata."""
        if not wikidata_id:
            return 'U', "Unknown"

        try:
            params = {
                'action': 'wbgetentities', 'ids': wikidata_id,
                'format': 'json', 'props': 'claims'
            }
            response = requests.get(WIKIDATA_API_URL, params=params, headers=HEADERS, timeout=10)
            response.raise_for_status()
            entities = response.json().get('entities', {})
            
            if wikidata_id not in entities:
                return 'U', "Unknown"

            claims = entities[wikidata_id].get('claims', {})

            # Get Gender (P21)
            gender_id = None
            gender = 'U' # Default to Unknown
            if 'P21' in claims:
                gender_id = claims['P21'][0]['mainsnak']['datavalue']['value']['id']
                if gender_id == 'Q6581097': gender = 'M'  # Male
                elif gender_id == 'Q6581072': gender = 'F'  # Female
                elif gender_id == 'Q1048413': gender = 'N'  # Non-binary

            # Get Nationality (P27)
            nationality_id = None
            nationality = "Unknown"
            if 'P27' in claims:
                # Get the *first* nationality listed
                nationality_id = claims['P27'][0]['mainsnak']['datavalue']['value']['id']
                nationality = self._get_wikidata_label(nationality_id)

            return gender, nationality

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"_get_wikidata_details error: {e}"))
            return 'U', "Unknown"

    def _get_wikidata_label(self, entity_id):
        """Helper function to get the English label for a Wikidata entity ID."""
        try:
            params = {
                'action': 'wbgetentities', 'ids': entity_id,
                'format': 'json', 'props': 'labels', 'languages': 'en'
            }
            response = requests.get(WIKIDATA_API_URL, params=params, headers=HEADERS, timeout=10)
            response.raise_for_status()
            entities = response.json().get('entities', {})
            if entity_id in entities:
                return entities[entity_id]['labels']['en']['value']
            return "Unknown"
        except Exception:
            return "Unknown"