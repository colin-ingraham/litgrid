from django.core.management.base import BaseCommand, CommandError
from library.models import Author
import requests
import time

class Command(BaseCommand):
    help = "Updates nationality for all authors in the database"

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit the number of authors to update (for testing)'
        )

    def get_nationality(self, author_key, headers):
        """Helper method to fetch nationality for a single author"""
        try:
            # Step 1: Get OpenLibrary author data
            ol_url = f"https://openlibrary.org/authors/{author_key}.json"
            ol_response = requests.get(ol_url, headers=headers, timeout=10)
            
            if ol_response.status_code != 200:
                return None
            
            ol_data = ol_response.json()
            
            # Step 2: Extract Wikidata ID
            wikidata_id = ol_data.get('remote_ids', {}).get('wikidata')
            
            if not wikidata_id:
                return None
            
            # Step 3: Query Wikidata
            wd_url = "https://www.wikidata.org/w/api.php"
            wd_params = {
                'action': 'wbgetentities',
                'ids': wikidata_id,
                'format': 'json',
                'props': 'claims'
            }
            
            wd_response = requests.get(wd_url, params=wd_params, headers=headers, timeout=10)
            
            if wd_response.status_code != 200:
                return None
                
            wd_data = wd_response.json()
            
            # Step 4: Extract nationality (P27 = country of citizenship)
            entity = wd_data['entities'][wikidata_id]
            claims = entity.get('claims', {})
            nationality_claims = claims.get('P27', [])
            
            if not nationality_claims:
                return None
            
            # Get the first nationality ID
            nationality_id = nationality_claims[0]['mainsnak']['datavalue']['value']['id']
            
            # Step 5: Get the country name
            country_params = {
                'action': 'wbgetentities',
                'ids': nationality_id,
                'format': 'json',
                'props': 'labels'
            }
            
            country_response = requests.get(wd_url, params=country_params, headers=headers, timeout=10)
            
            if country_response.status_code != 200:
                return None
                
            country_data = country_response.json()
            country_name = country_data['entities'][nationality_id]['labels']['en']['value']
            
            return country_name
                
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"    Error: {e}"))
            return None

    def handle(self, *args, **options):
        # Set a User-Agent header (required by Wikidata)
        headers = {
            'User-Agent': 'Litgrid/1.0 (https://github.com/colin-ingraham/litgrid; colinringraham@email.com)'
        }
        
        # Get all authors with Unknown nationality
        authors = Author.objects.filter(nationality="Unknown")
        
        # Apply limit if specified
        if options['limit']:
            authors = authors[:options['limit']]
        
        total = authors.count()
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No authors need updating!"))
            return
        
        self.stdout.write(f"Updating nationality for {total} authors...\n")
        
        success_count = 0
        fail_count = 0
        
        for i, author in enumerate(authors, 1):
            self.stdout.write(f"[{i}/{total}] {author.name} ({author.key})...")
            
            try:
                nationality = self.get_nationality(author.key, headers)
                
                if nationality:
                    author.nationality = nationality
                    author.save()
                    success_count += 1
                    self.stdout.write(self.style.SUCCESS(f"    ✓ {nationality}"))
                else:
                    fail_count += 1
                    self.stdout.write(self.style.WARNING(f"    ✗ No nationality data found"))
                
                # Be nice to the APIs - rate limit (1 request every 0.5 seconds)
                time.sleep(0.5)
                
            except Exception as e:
                fail_count += 1
                self.stdout.write(self.style.ERROR(f"    ✗ Failed: {e}"))
        
        # Summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS(f"Successfully updated: {success_count}"))
        self.stdout.write(self.style.WARNING(f"Failed: {fail_count}"))
        self.stdout.write("="*50)