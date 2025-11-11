# Primary Grid is LEGACY
# All the code below is no longer the algorithm used in Litgrid
# For the modern algorithm, referencing the Combinatorial Interesection Algorithm, otherwise referenced as CIA.py


"""" 
This is the algorithm for Primary Grid, the main Litgrid category generator 
that uses specific categories and an algorithm to generate daily Litgrids. 

        Misc   GenreV  Subject
       _______________________
Author |      |       |      |
       |______|_______|______|
Decade |      |       |      |
       |______|_______|______|
GenreH |      |       |      |
       |______|_______|______|

This is the format that PrimaryGrid will create. 
The colums and rows may be switched around, but that is the general structure.
Building it like this makes so that no cell is impossible to find a solution

The PG algorithm is going to assign a score to each Litgrid created. 
The score will determine its difficulty based on the following features:
- Number of possibilites per cell
- How popular the most likely book is in each cell

Difficulty Range per Cell:
<0 Books: Impossible (reject)
1-3 Books: Expert
4-10 Books: Hard
11-30 Books: Medium
31-50 Books: Easy
50+ Books: Too easy (reject)

All Possible Categories:
- Author (must be prominent)
- Decade (or Decade/Country i.e: Iceland 1950s)
- Genre
- Title Contains ___
- Award (NYT Bestseller)
- Subject
- Nationality of author (Icelandic Author)
- Author with first name ___

"""
from django.core.management.base import BaseCommand
from library.models import Book, Author
import random

AUTHOR_CAT_CHOICES = ["author", "nationality", "first_name", "author", "first_name"]
PRIMARY_SUBJECTS = ["science fiction", "historical fiction", "fantasy", "novela", 
                    "classic literature", "american literature", "classics", "african americans", 
                    "politics and government", "horror", "humor", "adventure", "thriller", "nonfiction", 
                    "fiction, coming of age", "romance", "magic", "drama", "detective and mystery stories", 
                    "adventure", "lawyers", "psychological fiction", "love", "murder", "farm life", "children's fiction"]

class Command(BaseCommand):

       def handle(self, *args, **options):
              
              # The categories are selected in the following process

              # 1. Get an author category
              author_cat, author = self.choose_author_cat()

              # 2. Choose Misc, GenreV and Subject based on Author
              subject = self.choose_subject(author_cat, author)
              self.test_author_subject_combo(author_cat, author, subject)
              # 3. Choose GenreH and Time Period based on column categories

              # 4. Verify playability
              

       
       def choose_author_cat(self):
              author_cat = random.choice(AUTHOR_CAT_CHOICES)
              if (author_cat == "first_name"):
                     author = self.get_author_with_first_name()
                     self.stdout.write(self.style.SUCCESS(f"Author category: Author with first name {author}"))
              elif (author_cat == "nationality"):
                     author = self.get_acceptable_country()
                     self.stdout.write(self.style.SUCCESS(f"Author category: Authors from {author}"))
              else: # Specific Author
                     author = self.get_prominent_author()
                     self.stdout.write(self.style.SUCCESS(f"Author category: Books by {author}"))
              return author_cat, author

       def get_author_with_first_name(self):
              authors = self.common_first_names()
              return random.choice(authors)
       
       def get_acceptable_country(self):
              countries = self.acceptable_country()
              return random.choice(countries)
       
       def get_prominent_author(self):
              authors = self.prominent_authors()
              return random.choice(authors)
       
       def prominent_authors(self):
              """" 
              This method is going to determine if an author is considered "prominent"
              To be prominent, an author must meet 2 criteria:
              1. At least 4 books in the database are published by the author
              2. NOT IMPLEMENTED - Top 100 authors of all time list (to make sure fantasy authors with 30 books don't get selected)

              """
              min_count = 4
              authors = {}
              prom_authors = []
              for book in Book.objects.all():
                     if book.author.name in authors:
                            authors[book.author.name] += 1
                     else:
                            authors[book.author.name] = 1
              for author in authors:
                     if authors[author] >= min_count:
                            prom_authors.append(author)
              return prom_authors

       def acceptable_country(self):
              # A country is 'acceptable' if it has less than 25 books and more than 3 in the database.
              max_books = 25
              min_books = 3
              countries = {}
              acceptable_countries = []
              for author in Author.objects.all():
                     # UK is a special circumstance since there are various nationalities that all mean UK
                     # Such as 'Kingdom of Great Britain', 'Kingdom of England', etc. 
                     if "Great Britain" in author.nationality or "United Kingdom" in author.nationality or "England" in author.nationality:
                            if "United Kingdom" not in countries:
                                   countries["United Kingdom"] = 1
                            else:
                                   countries["United Kingdom"] += 1
                     # Russia is the same way
                     elif "Russia" in author.nationality:
                            if "Russia" not in countries:
                                   countries["Russia"] = 1
                            else:
                                   countries["Russia"] += 1
                     # So is Germany
                     elif "Germany" in author.nationality or "German" in author.nationality:
                            if "Germany" not in countries:
                                   countries["Germany"] = 1
                            else:
                                   countries["Germany"] += 1
                     elif author.nationality not in countries:
                            countries[author.nationality] = 1
                     else:
                            countries[author.nationality] += 1
              for country in countries:
                     if countries[country] > min_books and countries[country] < max_books:
                            acceptable_countries.append(country)
              return acceptable_countries
       
       def common_first_names(self):
              # This method is going to return a list of the most common first names in my dataset.
              # This will be used to choose a name for the first_name author category
              min_count = 4
              names = {}
              common_names = []
              for author in Author.objects.all():
                     if author.first_name in names:
                            names[author.first_name] += 1
                     else:
                            names[author.first_name] = 1
              for name in names:
                     if names[name] >= min_count:
                            common_names.append(name)

              return common_names

       def get_authors_from_cat(self, author_cat, author):
              # This method is going to return the authors upon which the Author cat can be.
              authors = []
              if author_cat == "first_name":
                     for x in Author.objects.all():
                            if x.first_name == author:
                                   authors.append(x.name)
              elif author_cat == "nationality":
                     for x in Author.objects.all():
                            if x.nationality == author:
                                   authors.append(x.name)          
              else:
                     authors.append(author)
              return authors

       def get_author_prominent_subjects(self, author_cat, author):
              # This method is going to return a list of the most common subjects from a specific author/authors
              # One of these subjects will be chosen as the subject used in the grid.
              
              min_books = 2
              possible_authors = self.get_authors_from_cat(author_cat, author)
              subject_counts = {}
              prominent_subjects = []

              for a in possible_authors:
                     books = list(Book.objects.filter(author__name=a))
                     for book in books:
                            subjects = book.subjects.all()
                            for subject in subjects:
                                   if subject.name in subject_counts:
                                          subject_counts[subject.name] += 1
                                   else:
                                          subject_counts[subject.name] = 1
              
              for key, var in subject_counts.items():
                     if var >= min_books:
                            prominent_subjects.append(key)

              return prominent_subjects

       def choose_subject(self, author_cat, author):
              # This method is going to actually choose the subject for the grid.
              # If the author's prominent subjects contains one of the PRIMARY_SUBJECTS, then it will choose one of those.
              # Otherwise, it will choose one of the most likely, often under certain restraints. 

              prom_subs = self.get_author_prominent_subjects(author_cat, author)
              candidates = []
              for subject in prom_subs:
                     if subject in PRIMARY_SUBJECTS:
                            candidates.append(subject)
              if len(candidates) >= 1:
                     choice = random.choice(candidates)
                     self.stdout.write(self.style.SUCCESS(f"Subject category: {choice}"))
                     return choice
              else:
                     self.stdout.write(self.style.SUCCESS(f"No popular subject category found."))
                     return "No Subject"

       def most_common_subjects(self):
              # This method finds the most common subjects of all books. 
              # It is not used in the primary grid, but instead used manually to create the PRIMARY_SUBJECTS list for subject selection
              subject_min = 5
              subject_counts = {}
              books = list(Book.objects.all())
              for book in books:
                     subjects = book.subjects.all()
                     for subject in subjects:
                            if subject.name in subject_counts:
                                   subject_counts[subject.name] += 1
                            else:
                                   subject_counts[subject.name] = 1
              sorted_subjects = {k: v for k, v in sorted(subject_counts.items(), key=lambda item: item[1], reverse=True) if v >= subject_min}
              return sorted_subjects

       def test_author_subject_combo(self, author_cat, author, subject):
              # Returns the books possible for the given author and subject
              if subject != "No Subject":
                     authors = self.get_authors_from_cat(author_cat, author)
                     books = Book.objects.filter(subjects__name=subject, author__name__in=authors)
                     self.stdout.write(self.style.SUCCESS(f"Possible books for Cell 3 (Author/Subject): {books}"))
              
              


              
