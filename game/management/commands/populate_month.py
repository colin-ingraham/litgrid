from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from game.models import DailyPuzzle
from game.utils import generate_puzzle_for_date

class Command(BaseCommand):
    help = 'Generates LitGrid puzzles for today and the next 29 days (30 days total).'

    def add_arguments(self, parser):
        # Optional: Add a flag to force overwrite existing puzzles
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite existing puzzles if they already exist for a date.',
        )

    def handle(self, *args, **kwargs):
        start_date = timezone.now().date()
        days_to_generate = 30
        overwrite = kwargs['overwrite']

        self.stdout.write(f"Generating puzzles for {days_to_generate} days starting {start_date}...")

        for i in range(days_to_generate):
            target_date = start_date + timedelta(days=i)
            
            # Logic to handle overwriting
            if overwrite:
                deleted_count, _ = DailyPuzzle.objects.filter(date=target_date).delete()
                if deleted_count > 0:
                    self.stdout.write(f"Deleted existing puzzle for {target_date}")

            try:
                # This calls your existing logic which picks random categories
                puzzle = generate_puzzle_for_date(target_date)
                
                self.stdout.write(self.style.SUCCESS(f"[{target_date}] Success: {puzzle}"))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{target_date}] Failed: {e}"))

        self.stdout.write(self.style.SUCCESS("\nMonthly batch generation complete!"))