"""
Management command to create initial packages
"""
from django.core.management.base import BaseCommand
from packages.models import Package


class Command(BaseCommand):
    help = 'Create initial packages (Regular and ProSeller)'

    def handle(self, *args, **options):
        packages_data = [
            {
                'name': 'Regular Monthly',
                'package_type': 'regular',
                'duration_type': 'monthly',
                'price': 999.00,
                'duration_days': 30,
                'description': 'Basic package for regular users with essential features.',
                'max_listings': 10,
                'max_images_per_listing': 3,
                'featured_listings': 1,
                'priority_support': False,
                'analytics_access': False,
                'bulk_upload': False,
                'api_access': False,
                'is_active': True,
                'is_popular': False,
                'sort_order': 1
            },
            {
                'name': 'Regular Yearly',
                'package_type': 'regular',
                'duration_type': 'yearly',
                'price': 9999.00,
                'duration_days': 365,
                'description': 'Annual regular package with 2 months free.',
                'max_listings': 10,
                'max_images_per_listing': 3,
                'featured_listings': 12,  # 1 per month
                'priority_support': False,
                'analytics_access': True,
                'bulk_upload': False,
                'api_access': False,
                'is_active': True,
                'is_popular': True,
                'sort_order': 2
            },
            {
                'name': 'ProSeller Monthly',
                'package_type': 'proseller',
                'duration_type': 'monthly',
                'price': 2999.00,
                'duration_days': 30,
                'description': 'Professional package for business users with advanced features.',
                'max_listings': 0,  # Unlimited
                'max_images_per_listing': 10,
                'featured_listings': 5,
                'priority_support': True,
                'analytics_access': True,
                'bulk_upload': True,
                'api_access': True,
                'is_active': True,
                'is_popular': False,
                'sort_order': 3
            },
            {
                'name': 'ProSeller Yearly',
                'package_type': 'proseller',
                'duration_type': 'yearly',
                'price': 29999.00,
                'duration_days': 365,
                'description': 'Annual ProSeller package with maximum benefits.',
                'max_listings': 0,  # Unlimited
                'max_images_per_listing': 15,
                'featured_listings': 60,  # 5 per month
                'priority_support': True,
                'analytics_access': True,
                'bulk_upload': True,
                'api_access': True,
                'is_active': True,
                'is_popular': True,
                'sort_order': 4
            },
            {
                'name': 'ProSeller Lifetime',
                'package_type': 'proseller',
                'duration_type': 'lifetime',
                'price': 99999.00,
                'duration_days': 0,  # Lifetime
                'description': 'One-time payment for lifetime ProSeller access.',
                'max_listings': 0,  # Unlimited
                'max_images_per_listing': 20,
                'featured_listings': 1000,  # Very generous
                'priority_support': True,
                'analytics_access': True,
                'bulk_upload': True,
                'api_access': True,
                'is_active': True,
                'is_popular': False,
                'sort_order': 5
            }
        ]

        created_count = 0
        for package_data in packages_data:
            package, created = Package.objects.get_or_create(
                name=package_data['name'],
                defaults=package_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created package: {package.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Package already exists: {package.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} packages')
        )