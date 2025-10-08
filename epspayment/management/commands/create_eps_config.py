"""
Django management command to create EPS configuration
"""
from django.core.management.base import BaseCommand
from epspayment.models import EpsConfiguration


class Command(BaseCommand):
    help = 'Create a test EPS configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--name',
            type=str,
            default='Test EPS Configuration',
            help='Name of the EPS configuration'
        )
        parser.add_argument(
            '--merchant-id',
            type=str,
            default='TEST_MERCHANT_001',
            help='EPS Merchant ID'
        )
        parser.add_argument(
            '--store-id',
            type=str,
            default='TEST_STORE_001',
            help='EPS Store ID'
        )

    def handle(self, *args, **options):
        # Check if active config already exists
        existing_config = EpsConfiguration.objects.filter(is_active=True).first()
        if existing_config:
            self.stdout.write(
                self.style.WARNING(f'Active EPS configuration already exists: {existing_config.name}')
            )
            return

        # Create new configuration
        config = EpsConfiguration.objects.create(
            name=options['name'],
            merchant_id=options['merchant_id'],
            store_id=options['store_id'],
            merchant_key='test_merchant_key_12345678901234567890',
            hash_key='test_hash_key_12345678901234567890',
            base_url='https://sandbox.eps.com.bd',
            success_url='/payment/success',
            failure_url='/payment/failed',
            cancel_url='/payment/cancelled',
            is_active=True,
            description='Test configuration created by management command'
        )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created EPS configuration: {config.name}')
        )
        self.stdout.write(f'Merchant ID: {config.merchant_id}')
        self.stdout.write(f'Store ID: {config.store_id}')
        self.stdout.write(f'Base URL: {config.base_url}')
        self.stdout.write(
            self.style.WARNING('⚠️  This is a test configuration. Update with real credentials in production.')
        )