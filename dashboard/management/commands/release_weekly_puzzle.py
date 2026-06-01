"""
Management command: release_weekly_puzzle
Run every Sunday at 00:00 via Railway cron.

What it does:
1. Finds the next queued puzzle (complete, no release_date, lowest id).
2. Sets its release_date to today.
3. Checks if another queued puzzle exists after that one.
   If not, sends a warning email so you can prepare one.
"""

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone


class Command(BaseCommand):
    help = 'Releases the next queued puzzle and warns if backlog is empty.'

    def handle(self, *args, **options):
        from dashboard.models import ConnectionsPuzzle

        today = timezone.now().date()

        # ── Find next unreleased complete puzzle ──────────────────────────────
        next_puzzle = (
            ConnectionsPuzzle.objects
            .filter(release_date__isnull=True)
            .order_by('id')
            .first()
        )

        if not next_puzzle:
            self.stdout.write(self.style.WARNING('No queued puzzles found. Nothing released.'))
            self._send_warning_email(
                subject='⚠️ Litgrid: No puzzle to release this week',
                body=(
                    'The weekly release ran but found no queued puzzles.\n\n'
                    'No puzzle was released today. Please add one to the backlog immediately.'
                )
            )
            return

        if not next_puzzle.is_complete():
            self.stdout.write(self.style.WARNING(
                f'Next queued puzzle #{next_puzzle.id} is incomplete. Skipping.'
            ))
            self._send_warning_email(
                subject='⚠️ Litgrid: Next puzzle is incomplete',
                body=(
                    f'The weekly release found puzzle #{next_puzzle.id} but it is incomplete '
                    f'(missing groups or books).\n\nNo puzzle was released. Please fix it.'
                )
            )
            return

        # ── Release it ────────────────────────────────────────────────────────
        next_puzzle.release_date = today
        next_puzzle.save(update_fields=['release_date'])
        self.stdout.write(self.style.SUCCESS(
            f'Released puzzle #{next_puzzle.id} for {today}.'
        ))

        # ── Check if backlog has another one ready ────────────────────────────
        remaining = (
            ConnectionsPuzzle.objects
            .filter(release_date__isnull=True)
            .order_by('id')
            .count()
        )

        if remaining == 0:
            self.stdout.write(self.style.WARNING('Backlog is now empty — sending alert email.'))
            self._send_warning_email(
                subject='⚠️ Litgrid: Puzzle backlog is empty',
                body=(
                    f'Puzzle #{next_puzzle.id} was released today ({today}).\n\n'
                    'The backlog is now empty. No puzzle is queued for next Sunday.\n\n'
                    'Please create and publish a new puzzle before next week.'
                )
            )
        else:
            self.stdout.write(f'{remaining} puzzle(s) remaining in backlog.')

    def _send_warning_email(self, subject, body):
        admin_email = getattr(settings, 'ADMIN_EMAIL', None)
        if not admin_email:
            self.stdout.write(self.style.WARNING(
                'ADMIN_EMAIL not set in settings — cannot send alert.'
            ))
            return
        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@litgrid.app'),
                recipient_list=[admin_email],
                fail_silently=False,
            )
            self.stdout.write(f'Alert email sent to {admin_email}.')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send email: {e}'))