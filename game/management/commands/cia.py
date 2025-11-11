"""
This is the Combinatorial Intersection Algorithm, the modern algorithm used to create the daily Litgrid puzzle
Unlike Primary Grid which was constraining and predictable, the CIA creates a unique fun puzzle each time. 

Below is an explanation of the workings of the CIA:

1. Independent Category Selection (The "Pool")
    a. Ignoring the grid, select 6 categories at random. (Author, Decade, Genre, Award, etc.)
        - Rule: Ensure a diverse mix is selected (At least 2 author-based, 1 time-based, 2 subject-based).
        - Filter: Reject any category that is "Too Easy" (e.g., a category with 80% of database) 
                  or "Too Hard" (e.g., a category with two obscure novels).

    b. Assign to Grid (Randomize)
        - Randomly assign these 6 categories to the 3 column and row headers

2. Playability and Difficulty Scoring (The "Validation")
    a. Iterate over 9 Cells
        - For each cell at (Ri, Cj), query the database for the number of books that satisfy both criteria.
    b. Calculate Cell Score based on its count and the popularity of the best book.
        Rarity Score = log2 ( Total Books in DB / Cell Count + 1)
        Final Cell Score = (Rarity Score) x (Most Popular Book's Rating Score)
    c. If any cell count is 0 (impossible), or if more than 3 cells are Expert (1-3 books), 
       immediately reject the entire puzzle and restart the process

3. Final Selection (The "Polish")
    a. Calculate Total Puzzle Score
        - Sum the scores of the 9 cells. This gives an objective difficulty rating for the entire puzzle.
    b. Select Best Puzzle 
        - Run this generation processs N times and select the valid puzzle whose total score is closest to target difficulty

"""


from django.core.management.base import BaseCommand
from library.models import Book, Author
import random

""" 
LITGRID CIA CATEGORIES 

Author Categories ( 2 Per Round )

    - Gender/Pronoun (Female Author)
    - Debut Novel 
    - Author name (John Steinbeck)
    - Author with first name ___
    - Author nationality
    - 

Setting ( 1 Per Round )
    - Set in [Continent/Region]
    - Set in [Specific City]
    - Set in Fictional World
    - Set During [Historical Event / Era]
    - Environment: Farm/Ocean/Space
    
Title ( 0-1 Per Round )
    - Title contains ___
    - Title is single word
    - 

Genre ( 1 Per Round )
    - Specific Genre (Fantasy, Classic Lit)

Metadata ( 1-2 Per Round )
    - Written in ___ year
    - Award (NYT Bestseller)
    - Length
    - Banned Book

"""

class Command(BaseCommand):

    def handle(self, *args, **options):
        self.independentCatSelection()
       


    def independentCatSelection(self):
        categories = self.drawSix()

    def drawSix(self):
        # This method will gather 6 categories that will be used in the grid.
        categories = [self.choose_genre()]
        return categories

    def choose_genre(self):
        # A genre will always be one of the categories, chosen from this specific list.
        PRIMARY_GENRES = ["science fiction", "historical fiction", "fantasy", "novela", 
                    "classic literature", "american literature", "classics", "african americans", 
                    "politics and government", "horror", "humor", "adventure", "thriller", "nonfiction", 
                    "romance", "drama", "detective and mystery stories", 
                    "psychological fiction", "children's fiction"]
        genre = random.choice(PRIMARY_GENRES)
        return genre
    
    def choose_setting(self):
        # A setting category will always be one of the categories, chosen by this method.
        settingOptions = ["Region", "City", "Fictional", "Event", "Environment", "Event"]
        settingCat = random.choice(settingOptions)

        if settingCat == "Fictional":
            return ""
        
    