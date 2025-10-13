"""
Management command to populate initial survey type pricing
"""
from django.core.management.base import BaseCommand
from packages.models import SurveyTypePricing
from decimal import Decimal


class Command(BaseCommand):
    help = 'Populate initial survey type pricing data'

    def handle(self, *args, **kwargs):
        survey_types_data = [
            {
                'survey_type': 'SA_RS',
                'display_name': 'SA/RS সার্ভে',
                'base_price': Decimal('15.00'),
                'description': 'SA এবং RS সার্ভে টাইপের জন্য মূল্য',
                'sort_order': 1
            },
            {
                'survey_type': 'CS',
                'display_name': 'CS সার্ভে',
                'base_price': Decimal('20.00'),
                'description': 'CS সার্ভে টাইপের জন্য মূল্য',
                'sort_order': 2
            },
            {
                'survey_type': 'BS',
                'display_name': 'BS সার্ভে',
                'base_price': Decimal('25.00'),
                'description': 'BS সার্ভে টাইপের জন্য মূল্য',
                'sort_order': 3
            },
            {
                'survey_type': 'SA',
                'display_name': 'SA সার্ভে',
                'base_price': Decimal('15.00'),
                'description': 'SA সার্ভে টাইপের জন্য মূল্য',
                'sort_order': 4
            },
            {
                'survey_type': 'RS',
                'display_name': 'RS সার্ভে',
                'base_price': Decimal('15.00'),
                'description': 'RS সার্ভে টাইপের জন্য মূল্য',
                'sort_order': 5
            },
        ]

        created_count = 0
        updated_count = 0

        for data in survey_types_data:
            survey_type, created = SurveyTypePricing.objects.update_or_create(
                survey_type=data['survey_type'],
                defaults={
                    'display_name': data['display_name'],
                    'base_price': data['base_price'],
                    'description': data['description'],
                    'sort_order': data['sort_order'],
                    'is_active': True
                }
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Created: {survey_type.survey_type} - ৳{survey_type.base_price}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'🔄 Updated: {survey_type.survey_type} - ৳{survey_type.base_price}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✨ Complete! Created: {created_count}, Updated: {updated_count}'
            )
        )
