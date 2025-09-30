from django.core.management.base import BaseCommand
import requests

class Command(BaseCommand):
    help = "Queries for one book."

    def handle(self, *args, **options): 
        url = f"https://openlibrary.org/search.json?q=the+lord+of+the+rings"
        response = requests.get(url).json()
        self.stdout.write(self.style.SUCCESS(f'{response}'))