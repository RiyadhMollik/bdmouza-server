"""
Debug command to check package activation status
"""
from django.core.management.base import BaseCommand
from packages.models import UserPackage
from epspayment.models import EpsTransaction


class Command(BaseCommand):
    help = 'Debug package activation for a specific transaction'

    def add_arguments(self, parser):
        parser.add_argument(
            '--transaction-id',
            type=str,
            help='Transaction ID to debug',
        )
        parser.add_argument(
            '--user-package-id',
            type=int,
            help='UserPackage ID to debug',
        )

    def handle(self, *args, **options):
        transaction_id = options.get('transaction_id')
        user_package_id = options.get('user_package_id')
        
        if transaction_id:
            # Find EPS transaction
            try:
                eps_transaction = EpsTransaction.objects.get(merchant_transaction_id=transaction_id)
                self.stdout.write(f"EPS Transaction found:")
                self.stdout.write(f"  - ID: {eps_transaction.id}")
                self.stdout.write(f"  - Customer Order ID: {eps_transaction.customer_order_id}")
                self.stdout.write(f"  - Status: {eps_transaction.status}")
                self.stdout.write(f"  - Payment Status: {eps_transaction.payment_status}")
                self.stdout.write(f"  - Created: {eps_transaction.created_at}")
                self.stdout.write(f"  - Completed: {eps_transaction.completed_at}")
                
                # Extract user_package_id from customer_order_id
                if eps_transaction.customer_order_id and eps_transaction.customer_order_id.startswith('PKG-'):
                    extracted_id = eps_transaction.customer_order_id.replace('PKG-', '')
                    self.stdout.write(f"  - Extracted UserPackage ID: {extracted_id}")
                    
                    try:
                        user_package = UserPackage.objects.get(id=extracted_id)
                        self.stdout.write(f"\nUserPackage found:")
                        self.stdout.write(f"  - ID: {user_package.id}")
                        self.stdout.write(f"  - User: {user_package.user.email}")
                        self.stdout.write(f"  - Package: {user_package.package.name}")
                        self.stdout.write(f"  - Status: {user_package.status}")
                        self.stdout.write(f"  - Start Date: {user_package.start_date}")
                        self.stdout.write(f"  - End Date: {user_package.end_date}")
                        self.stdout.write(f"  - Transaction ID: {user_package.transaction_id}")
                        self.stdout.write(f"  - Is Active: {user_package.is_active()}")
                        
                    except UserPackage.DoesNotExist:
                        self.stdout.write(f"  - ❌ UserPackage with ID {extracted_id} not found!")
                        
            except EpsTransaction.DoesNotExist:
                self.stdout.write(f"❌ EPS Transaction with ID {transaction_id} not found!")
                
        elif user_package_id:
            try:
                user_package = UserPackage.objects.get(id=user_package_id)
                self.stdout.write(f"UserPackage found:")
                self.stdout.write(f"  - ID: {user_package.id}")
                self.stdout.write(f"  - User: {user_package.user.email}")
                self.stdout.write(f"  - Package: {user_package.package.name}")
                self.stdout.write(f"  - Status: {user_package.status}")
                self.stdout.write(f"  - Start Date: {user_package.start_date}")
                self.stdout.write(f"  - End Date: {user_package.end_date}")
                self.stdout.write(f"  - Transaction ID: {user_package.transaction_id}")
                self.stdout.write(f"  - Is Active: {user_package.is_active()}")
                
                # Try to activate manually if not active
                if user_package.status != 'active':
                    self.stdout.write(f"\n🔧 Attempting manual activation...")
                    user_package.activate_package()
                    self.stdout.write(f"✅ Package activated!")
                    self.stdout.write(f"  - New Status: {user_package.status}")
                    self.stdout.write(f"  - Start Date: {user_package.start_date}")
                    self.stdout.write(f"  - End Date: {user_package.end_date}")
                    
            except UserPackage.DoesNotExist:
                self.stdout.write(f"❌ UserPackage with ID {user_package_id} not found!")
        else:
            self.stdout.write("Please provide either --transaction-id or --user-package-id")