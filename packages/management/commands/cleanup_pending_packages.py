"""
Management command to cleanup old pending packages
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from packages.models import UserPackage


class Command(BaseCommand):
    help = 'Cleanup old pending package purchases (older than 2 hours)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=2,
            help='Age in hours for packages to be considered old (default: 2)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        hours = options['hours']
        dry_run = options['dry_run']
        
        # Find pending packages older than specified hours
        cutoff_time = timezone.now() - timedelta(hours=hours)
        old_pending_packages = UserPackage.objects.filter(
            status='pending',
            created_at__lt=cutoff_time
        )
        
        count = old_pending_packages.count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would delete {count} pending packages older than {hours} hours'
                )
            )
            if count > 0:
                self.stdout.write("Packages that would be deleted:")
                for pkg in old_pending_packages[:10]:  # Show first 10
                    self.stdout.write(
                        f"  - ID: {pkg.id}, User: {pkg.user.email}, Package: {pkg.package.name}, "
                        f"Created: {pkg.created_at}, Transaction: {pkg.transaction_id}"
                    )
                if count > 10:
                    self.stdout.write(f"  ... and {count - 10} more")
        else:
            # Actually delete the packages
            deleted_count = old_pending_packages.delete()[0]
            
            if deleted_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully deleted {deleted_count} old pending packages'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('No old pending packages found to delete')
                )