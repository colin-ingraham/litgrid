# This method checks if an author has an abbreviation in their name. Like George R.R. Martin
def checkAuthorAbbreviation(author):
    for index, letter in enumerate(author):
        if letter.isupper():
            if index + 1 < len(author) and author[index + 1] == ".":
                return True
    return False