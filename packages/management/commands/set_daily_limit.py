"""
Django management command to set daily order limit for all packages
"""
from django.core.management.base import BaseCommand
from packages.models import Package


class Command(BaseCommand):
    help = 'Set daily order limit for all packages'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='Daily order limit to set (default: 20)',
        )

    def handle(self, *args, **options):
        limit = options['limit']
        
        # Update all packages
        updated_count = Package.objects.update(daily_order_limit=limit)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated {updated_count} packages with daily_order_limit = {limit}'
            )
        )
        
        # Show updated packages
        self.stdout.write('\nUpdated packages:')
        for package in Package.objects.all():
            self.stdout.write(
                f'  • {package.name}: {package.daily_order_limit} orders per day'
            )