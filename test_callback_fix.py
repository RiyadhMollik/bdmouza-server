#!/usr/bin/env python
"""
Test script to verify EPS callback handler fixes
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'starterproject.settings')
django.setup()

from others.models import Purchases
from epspayment.models import EpsTransaction
from django.utils import timezone

print("=" * 60)
print("EPS CALLBACK FIX VERIFICATION")
print("=" * 60)

# Check recent EPS transactions
print("\n📊 Recent EPS Transactions:")
print("-" * 60)
recent_transactions = EpsTransaction.objects.all().order_by('-created_at')[:5]
for txn in recent_transactions:
    print(f"TRX ID: {txn.merchant_transaction_id}")
    print(f"  Order ID: {txn.customer_order_id}")
    print(f"  Order Type: {txn.order_type}")
    print(f"  Status: {txn.status}")
    print(f"  Email: {txn.customer_email}")
    print(f"  Amount: {txn.amount}")
    print()

# Check recent purchases
print("\n📋 Recent Purchases:")
print("-" * 60)
recent_purchases = Purchases.objects.all().order_by('-created_at')[:5]
for purchase in recent_purchases:
    print(f"Purchase ID: {purchase.id}")
    print(f"  User: {purchase.user.email if purchase.user else 'N/A'}")
    print(f"  TRX Number: {purchase.trx_number}")
    print(f"  Payment Status: {purchase.payment_status}")
    print(f"  Amount: {purchase.amount}")
    print(f"  Payment Method: {purchase.payment_method}")
    print(f"  Created: {purchase.created_at}")
    print()

# Check for orphaned transactions (completed but no matching purchase)
print("\n⚠️  Orphaned Transactions (completed but no matching purchase):")
print("-" * 60)
completed_txns = EpsTransaction.objects.filter(
    status='completed',
    order_type='file'
).order_by('-created_at')[:10]

orphaned_count = 0
for txn in completed_txns:
    # Try to find matching purchase
    matching_purchase = Purchases.objects.filter(trx_number=txn.merchant_transaction_id).first()
    
    if not matching_purchase:
        # Try extracting from order_id
        if txn.customer_order_id and txn.customer_order_id.startswith('ORD-'):
            parts = txn.customer_order_id.split('-')
            if len(parts) >= 2:
                try:
                    purchase_id = int(parts[1])
                    matching_purchase = Purchases.objects.filter(id=purchase_id).first()
                except ValueError:
                    pass
    
    if not matching_purchase:
        orphaned_count += 1
        print(f"❌ TRX: {txn.merchant_transaction_id}")
        print(f"   Order ID: {txn.customer_order_id}")
        print(f"   Email: {txn.customer_email}")
        print(f"   No matching Purchase found!")
        print()

if orphaned_count == 0:
    print("✅ No orphaned transactions found!")

print("\n" + "=" * 60)
print(f"Total Transactions: {EpsTransaction.objects.count()}")
print(f"Total Purchases: {Purchases.objects.count()}")
print(f"Completed EPS Transactions: {EpsTransaction.objects.filter(status='completed').count()}")
print(f"Completed Purchases: {Purchases.objects.filter(payment_status='completed').count()}")
print("=" * 60)
