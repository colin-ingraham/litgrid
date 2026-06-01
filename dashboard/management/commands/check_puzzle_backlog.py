"""
Management command: check_puzzle_backlog
Run every Saturday at 00:00 via Railway cron — 24h warning before weekly release.
"""

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Checks puzzle backlog 24h before weekly release and warns if low.'

    def handle(self, *args, **options):
        from dashboard.models import ConnectionsPuzzle

        queued = (
            ConnectionsPuzzle.objects
            .filter(release_date__isnull=True)
            .order_by('id')
        )
        count = queued.count()

        if count == 0:
            self.stdout.write(self.style.WARNING('Backlog empty — sending 24h warning.'))
            self._send(
                subject='⚠️ Litgrid: No puzzle ready for Sunday',
                body=(
                    'This is your 24-hour warning.\n\n'
                    'There are NO queued puzzles in the backlog.\n\n'
                    'The Sunday release will find nothing to publish. '
                    'Please create and publish a puzzle before midnight tonight.'
                )
            )
        elif count == 1:
            next_up = queued.first()
            self.stdout.write(self.style.WARNING(
                f'Only 1 puzzle in backlog (#{next_up.id}). Sending low-stock warning.'
            ))
            self._send(
                subject='📋 Litgrid: Puzzle backlog running low',
                body=(
                    f'This is your 24-hour heads-up.\n\n'
                    f'Puzzle #{next_up.id} will be released tomorrow (Sunday).\n\n'
                    f'After that, the backlog will be empty. '
                    f'Please queue at least one more puzzle soon.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Backlog looks good — {count} puzzles queued.')
            )

    def _send(self, subject, body):
        import resend
        admin_email = getattr(settings, 'ADMIN_EMAIL', None)
        if not admin_email:
            self.stdout.write(self.style.WARNING('ADMIN_EMAIL not set — cannot send alert.'))
            return
        resend.api_key = getattr(settings, 'RESEND_API_KEY', '')
        if not resend.api_key:
            self.stdout.write(self.style.WARNING('RESEND_API_KEY not set — cannot send alert.'))
            return
        try:
            resend.Emails.send({
                'from':    'Litgrid <alerts@playlitgrid.com>',
                'to':      admin_email,
                'subject': subject,
                'text':    body,
            })
            self.stdout.write(f'Alert sent to {admin_email}.')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send email: {e}'))