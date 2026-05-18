from django.shortcuts import render
import json
from datetime import date


def ConnectionsGame(request):
    sample_puzzle = {
        'groups': [
            {
                'category': 'One-Word Titles',
                'difficulty': 1,
                'books': [
                    {'title': 'Beloved', 'author': 'Toni Morrison'},
                    {'title': 'Dune', 'author': 'Frank Herbert'},
                    {'title': 'Frankenstein', 'author': 'Mary Shelley'},
                    {'title': 'Lolita', 'author': 'Vladimir Nabokov'},
                ],
            },
            {
                'category': 'Set in a Dystopian Future',
                'difficulty': 2,
                'books': [
                    {'title': '1984', 'author': 'George Orwell'},
                    {'title': 'Brave New World', 'author': 'Aldous Huxley'},
                    {'title': "The Handmaid's Tale", 'author': 'Margaret Atwood'},
                    {'title': 'Fahrenheit 451', 'author': 'Ray Bradbury'},
                ],
            },
            {
                'category': 'Written by a Brontë',
                'difficulty': 3,
                'books': [
                    {'title': 'Jane Eyre', 'author': 'Charlotte Brontë'},
                    {'title': 'Wuthering Heights', 'author': 'Emily Brontë'},
                    {'title': 'The Tenant of Wildfell Hall', 'author': 'Anne Brontë'},
                    {'title': 'Agnes Grey', 'author': 'Anne Brontë'},
                ],
            },
            {
                'category': 'Color in the Title',
                'difficulty': 4,
                'books': [
                    {'title': 'The Color Purple', 'author': 'Alice Walker'},
                    {'title': 'The Scarlet Letter', 'author': 'Nathaniel Hawthorne'},
                    {'title': 'The Red Badge of Courage', 'author': 'Stephen Crane'},
                    {'title': 'Fifty Shades of Grey', 'author': 'E.L. James'},
                ],
            },
        ]
    }

    context = {
        'puzzle_data_json': json.dumps(sample_puzzle),
        'puzzle_date': date.today().strftime('%Y-%m-%d'),
        'display_date': date.today().strftime('%B %d, %Y'),
    }
    return render(request, 'connections/connections.html', context)
