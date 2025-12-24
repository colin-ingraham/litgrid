from django.core.management.base import BaseCommand
from game.models import Category

class Command(BaseCommand):
    help = 'Populates the database with the initial set of game categories.'

    def handle(self, *args, **kwargs):
        # --- PASTE YOUR CATEGORY LIST HERE ---
        # Format:
        # {
        #     "display_name": "Visible Name",
        #     "logic_code": "backend_code",
        #     "description": "Tooltip text"
        # },
        
        initial_categories = [
            {
                "display_name": "Fantasy",
                "logic_code": "SFantasy",
                "description": "Listed under Fantasy subjects or genres."
            },
            {
                "display_name": "Historical Fiction",
                "logic_code": "SHistorical",
                "description": "Listed under Historical Fiction subjects."
            },
            {
                "display_name": "Literary Fiction",
                "logic_code": "SLiterary",
                "description": "Listed under Literary Fiction or General Fiction subjects."
            },
            {
                "display_name": "Graphic Novels",
                "logic_code": "SGraphic Novels",
                "description": "Comics, Manga, or Graphic Novels."
            },
            {
                "display_name": "Romance",
                "logic_code": "SRomance",
                "description": "Listed under Romance subjects."
            },
            {
                "display_name": "Juvenile Fiction",
                "logic_code": "SJuvenile",
                "description": "Books categorized as Children's or Young Adult fiction."
            },
            {
                "display_name": "Poetry Collections",
                "logic_code": "SPoetry",
                "description": "Collections of poetry or single epic poems."
            },
            {
                "display_name": "Mystery",
                "logic_code": "SMystery",
                "description": "Listed under Mystery, Thriller, Crime, or Detective fiction."
            },
            {
                "display_name": "Horror",
                "logic_code": "SHorror",
                "description": "Listed under Horror subjects."
            },
            {
                "display_name": "Autobiography",
                "logic_code": "SAutobiography",
                "description": "Non-fiction accounts of a person's life written by that person."
            },

            # TIME CATEGORIES
            {
                "display_name": "From the 19th Century",
                "logic_code": "Tc19",
                "description": "Published between 1800 and 1899."
            },
            {
                "display_name": "From the 20th Century",
                "logic_code": "Tc20",
                "description": "Published between 1900 and 1999."
            },
            {
                "display_name": "From the 21st Century",
                "logic_code": "Tc21",
                "description": "Published in or after the year 2000."
            },
            {
                "display_name": "From the 2020s",
                "logic_code": "Td22",
                "description": "Published in 2020 or later."
            },
            {
                "display_name": "From the 2010s",
                "logic_code": "Td21",
                "description": "Published between 2010 and 2019."
            },
            {
                "display_name": "From the 1990s",
                "logic_code": "Td99",
                "description": "Published between 1990 and 1999."
            },
            {
                "display_name": "From the 1980s",
                "logic_code": "Td98",
                "description": "Published between 1980 and 1989."
            },
            {
                "display_name": "From the 1970s",
                "logic_code": "Td97",
                "description": "Published between 1970 and 1979."
            },
            {
                "display_name": "Published during World War 2",
                "logic_code": "Tp19391945",
                "description": "Published between 1939 and 1945."
            },
            {
                "display_name": "Published in a leap year",
                "logic_code": "Tmleap",
                "description": "Published in a year with 366 days (e.g., 2004, 2016)."
            },

            # LENGTH CATEGORIES
            {
                "display_name": "Books under 200 pages",
                "logic_code": "Lu200",
                "description": "Must have strictly fewer than 200 pages."
            },
            {
                "display_name": "Books over 600 pages",
                "logic_code": "Lo600",
                "description": "Must have 600 pages or more."
            },
            {
                "display_name": "Books over 1000 pages",
                "logic_code": "Lo1000",
                "description": "Must have 1000 pages or more."
            },

            # NAME CATEGORIES
            {
                "display_name": "One Word Title",
                "logic_code": "Nw1",
                "description": "Title consists of exactly one word (excluding subtitles)."
            },
            {
                "display_name": "Title has 7+ words",
                "logic_code": "Nw7+",
                "description": "The main title must contain 7 or more words."
            },
            {
                "display_name": "Title Starts with 'The'",
                "logic_code": "Nsthe",
                "description": "The very first word of the title must be 'The'."
            },
            {
                "display_name": "Title Contains a Number",
                "logic_code": "Ncnum",
                "description": "Title must include a number word (e.g. Seven) or a digit."
            },
            {
                "display_name": "Title Contains a Color",
                "logic_code": "Nccol",
                "description": "Title includes a color like Red, Blue, Green, Gold, etc."
            },
            {
                "display_name": "Title Contains a Family Member",
                "logic_code": "Ncfam",
                "description": "Title includes words like Sister, Father, Aunt, Son, etc."
            },
            {
                "display_name": "Title Contains a Season",
                "logic_code": "Ncsea",
                "description": "Title includes Spring, Summer, Autumn, Fall, or Winter."
            },

            # AUTHOR CATEGORIES
            {
                "display_name": "Author has alliterative name",
                "logic_code": "Aall",
                "description": "First and Last names start with the same letter (e.g., Jack Jones)."
            },
            {
                "display_name": "Author name has initials",
                "logic_code": "Aini",
                "description": "Author uses initials in their pen name (e.g., C.S. Lewis)."
            },
            {
                "display_name": "Single name Authors",
                "logic_code": "Asin",
                "description": "Author is known by a mononym (e.g., Plato)."
            },
            {
                "display_name": "Author with first name John",
                "logic_code": "ANjohn",
                "description": "Author's first name is John or Jon."
            },
            {
                "display_name": "Author with first name James",
                "logic_code": "ANjames",
                "description": "Author's first name is James."
            },
            {
                "display_name": "Author with first name Michael",
                "logic_code": "ANmichael",
                "description": "Author's first name is Michael or Mike."
            },
            {
                "display_name": "Author with first name Mary",
                "logic_code": "ANmary",
                "description": "Author's first name is Mary."
            },
            {
                "display_name": "Author with first name Susan",
                "logic_code": "ANsusan",
                "description": "Author's first name is Susan or Sue."
            }
        ]
        
        # --- LOGIC LOOP ---
        self.stdout.write("Starting category population...")
        
        count_created = 0
        count_updated = 0

        for data in initial_categories:
            # We use logic_code as the unique identifier.
            # This allows you to change display_name or description later 
            # and simply re-run this command to update the live site.
            obj, created = Category.objects.update_or_create(
                logic_code=data['logic_code'],
                defaults={
                    'display_name': data['display_name'],
                    'description': data['description'],
                    'is_active': True  # Default to active when added via script
                }
            )
            
            if created:
                count_created += 1
                self.stdout.write(self.style.SUCCESS(f"Created: {data['display_name']}"))
            else:
                count_updated += 1
                self.stdout.write(f"Updated: {data['display_name']}")

        self.stdout.write(self.style.SUCCESS(f"\nDone! Created {count_created} new, Updated {count_updated} existing."))