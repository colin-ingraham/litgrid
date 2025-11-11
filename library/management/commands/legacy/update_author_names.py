from django.core.management.base import BaseCommand, CommandError
from library.models import Author
import requests
import time
import re

class Command(BaseCommand):
    help = "Updates author names to English versions and fixes first/last name parsing"

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit the number of authors to update (for testing)'
        )

    def get_english_name(self, author_key, current_name, headers):
        """
        Fetches English name for an author using OpenLibrary and Wikidata.
        Returns the best English name or None if no better option found.
        """
        try:
            # Step 1: If current name is already ASCII and looks good, check if we can verify it
            if current_name and current_name.isascii():
                # Don't try to "fix" names that are already in normal format
                # Only fetch if name looks problematic (single letter, etc.)
                if len(current_name) > 3 and not self.looks_problematic(current_name):
                    return current_name
            
            # Step 2: Get OpenLibrary author data
            ol_url = f"https://openlibrary.org/authors/{author_key}.json"
            ol_response = requests.get(ol_url, headers=headers, timeout=10)
            
            if ol_response.status_code != 200:
                return None
            
            ol_data = ol_response.json()
            
            # Step 3: Try to get English name from OpenLibrary fields
            # Priority: personal_name > name (if better than current)
            personal_name = ol_data.get('personal_name', '')
            ol_name = ol_data.get('name', '')
            
            # Use personal_name if it's ASCII
            if personal_name and personal_name.isascii():
                return personal_name
            
            # Use ol_name if current is non-ASCII but ol_name is ASCII
            if ol_name and ol_name.isascii() and (not current_name.isascii()):
                return ol_name
            
            # Step 4: Check alternate_names for English version
            for alt_name in ol_data.get('alternate_names', []):
                if alt_name.isascii() and len(alt_name) > 3:
                    # Prefer names that don't have comma formatting
                    if ',' not in alt_name:
                        return alt_name
            
            # Step 5: Fall back to Wikidata English label
            wikidata_id = ol_data.get('remote_ids', {}).get('wikidata')
            if wikidata_id and not current_name.isascii():
                wd_url = "https://www.wikidata.org/w/api.php"
                wd_params = {
                    'action': 'wbgetentities',
                    'ids': wikidata_id,
                    'format': 'json',
                    'props': 'labels',
                    'languages': 'en'
                }
                
                wd_response = requests.get(wd_url, params=wd_params, headers=headers, timeout=10)
                
                if wd_response.status_code == 200:
                    wd_data = wd_response.json()
                    entity = wd_data['entities'][wikidata_id]
                    english_name = entity.get('labels', {}).get('en', {}).get('value')
                    
                    if english_name and english_name.isascii():
                        return english_name
            
            # If nothing better found, return None (keep current)
            return None
                
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"    Error fetching name: {e}"))
            return None

    def looks_problematic(self, name):
        """Check if a name looks problematic and needs fixing"""
        # Single letters or very short
        if len(name) <= 2:
            return True
        # Starts with single letter + period (but this is actually common and OK)
        return False

    def parse_name(self, full_name):
        """
        Parse a full name into first and last name intelligently.
        First name = actual first name only (skip initials if needed)
        Last name = actual last name only
        Returns tuple: (first_name, last_name)
        """
        if not full_name:
            return ('Unknown', 'Author')
        
        full_name = full_name.strip()
        
        # Handle "Last, First" format (e.g., "Walker, Alice")
        if ',' in full_name:
            parts = full_name.split(',')
            last_name = parts[0].strip()
            first_name = parts[1].strip().split()[0] if len(parts) > 1 else last_name
            return (first_name, last_name)
        
        parts = full_name.split()
        
        # Single name (e.g., "Homer", "Virgil")
        if len(parts) == 1:
            return (full_name, '')
        
        # Multiple parts strategy:
        # - First name = first non-initial part
        # - Last name = last part (always)
        
        # Find the first real name (not an initial)
        first_name = None
        for part in parts[:-1]:  # Don't include the last part in this search
            # Check if it's an initial (1-2 chars with optional period)
            if re.match(r'^[A-Z]\.?$', part):
                continue  # Skip initials
            else:
                first_name = part
                break
        
        # If all parts before last name were initials, use the first initial
        if not first_name:
            first_name = parts[0]
        
        # Last name is always the last part
        last_name = parts[-1]
        
        return (first_name, last_name)

    def handle(self, *args, **options):
        # Set a User-Agent header
        headers = {
            'User-Agent': 'Litgrid/1.0 (https://github.com/colin-ingraham/litgrid; colinringraham@email.com)'
        }
        
        # Get all authors
        authors = Author.objects.all()
        
        # Apply limit if specified
        if options['limit']:
            authors = authors[:options['limit']]
        
        total = authors.count()
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No authors to update!"))
            return
        
        self.stdout.write(f"Updating names for {total} authors...\n")
        
        success_count = 0
        unchanged_count = 0
        
        for i, author in enumerate(authors, 1):
            self.stdout.write(f"[{i}/{total}] {author.name} ({author.key})...")
            
            try:
                # Try to get a better English name
                better_name = self.get_english_name(author.key, author.name, headers)
                
                # Use the better name if found, otherwise use current
                final_name = better_name if better_name else author.name
                
                # Parse the name properly
                first_name, last_name = self.parse_name(final_name)
                
                # Check if anything actually changed
                changed = (final_name != author.name or 
                          first_name != author.first_name or 
                          last_name != author.last_name)
                
                if changed:
                    old_name = author.name
                    old_first = author.first_name
                    old_last = author.last_name
                    
                    author.name = final_name
                    author.first_name = first_name
                    author.last_name = last_name
                    author.save()
                    success_count += 1
                    
                    self.stdout.write(self.style.SUCCESS(
                        f"    ✓ Name: '{old_name}' → '{final_name}'"
                    ))
                    self.stdout.write(self.style.SUCCESS(
                        f"      First: '{old_first}' → '{first_name}' | Last: '{old_last}' → '{last_name}'"
                    ))
                else:
                    unchanged_count += 1
                    self.stdout.write(self.style.WARNING(f"    - No change needed"))
                
                # Be nice to the APIs - rate limit
                time.sleep(0.5)
                
            except Exception as e:
                unchanged_count += 1
                self.stdout.write(self.style.ERROR(f"    ✗ Failed: {e}"))
        
        # Summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS(f"Successfully updated: {success_count}"))
        self.stdout.write(self.style.WARNING(f"Unchanged: {unchanged_count}"))
        self.stdout.write("="*50)