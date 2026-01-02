import random
from datetime import date
from .models import Category, DailyPuzzle

def generate_puzzle_for_date(target_date=None):
    if target_date is None:
        target_date = date.today()

    # 1. Check if it already exists to prevent overwriting
    if DailyPuzzle.objects.filter(date=target_date).exists():
        print(f"Puzzle for {target_date} already exists.")
        return DailyPuzzle.objects.get(date=target_date)

    # 2. Get all active categories
    all_cats = list(Category.objects.filter(is_active=True))

    if len(all_cats) < 6:
        raise ValueError("Not enough categories to generate a puzzle!")

    # 3. Selection
    """ Selection for the Litgrid is relatively simple
    There are a few rules that define the way it can be made
    - No same category type can intersect
    - Most commonly you will see 2-3 Genres, and 3-4 of the following: Author, time, length, title based categories
    - These categories can be in any order, but the 2-3 genres cannot interflict (have to be on same side)

    """
    selected = []
    
    # A. Pick 2-3 Genres (Logic Codes start with 'S')
    genre_options = [cat for cat in all_cats if cat.logic_code.startswith("S")]
    num_genres = random.randint(2, 3)
    
    # Randomly pick unique genres
    genres = random.sample(genre_options, num_genres)
    selected.extend(genres) 

    # B. Fill the remaining spots (Total must be 6)
    spots_left = 6 - num_genres
    other_types = ["A", "N", "T", "L"] # Author, Name, Time, Length
    
    # We shuffle types so we don't always pick "A" then "N" then "T" in order
    random.shuffle(other_types) 

    others = []
    for type_code in other_types:
        if len(others) == spots_left:
            break
            
        # Find all categories matching this type code (e.g., all 'T' time cats)
        options_for_type = [cat for cat in all_cats if cat.logic_code.startswith(type_code)]
        
        if options_for_type:
            others.append(random.choice(options_for_type))

    # Safety check: if we ran out of unique types but still need spots (rare edge case)
    while len(others) < spots_left:
        leftovers = [c for c in all_cats if c not in genres and c not in others and not c.logic_code.startswith("S")]
        if not leftovers: break
        others.append(random.choice(leftovers))

    # --- 4. The "No Intersection" Shuffler ---
    # Currently 'selected' is [Genre, Genre, ..., Other, Other, Other]
    
    # Decide if Genres go on Rows (indices 0-2) or Cols (indices 3-5)
    genres_on_rows = random.choice([True, False])

    if genres_on_rows:
        # Rows get ALL genres + whatever others are needed to fill 3 spots
        # Cols get the remaining 'others'
        row_bucket = genres + others[:(3 - len(genres))]
        col_bucket = others[(3 - len(genres)):]
    else:
        # Cols get ALL genres + needed others
        # Rows get the remaining 'others'
        col_bucket = genres + others[:(3 - len(genres))]
        row_bucket = others[(3 - len(genres)):]

    # Now shuffle the buckets internally so "Fantasy" isn't always cell #1
    random.shuffle(row_bucket)
    random.shuffle(col_bucket)

    # Finalize
    selected = row_bucket + col_bucket

    # 4. Create the DailyPuzzle
    puzzle = DailyPuzzle.objects.create(
        date=target_date,
        row_1=selected[0],
        row_2=selected[1],
        row_3=selected[2],
        col_1=selected[3],
        col_2=selected[4],
        col_3=selected[5]
    )
    
    return puzzle