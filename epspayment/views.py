"""
EPS Payment Gateway Views
"""
import json
import logging
from datetime import datetime, timedelta

from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings
from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from .models import EpsConfiguration, EpsTransaction, EpsWebhookLog
from .utils import (
    get_eps_configuration, 
    get_eps_token, 
    generate_eps_hash, 
    generate_merchant_transaction_id,
    get_client_ip,
    get_callback_urls,
    validate_eps_callback_signature
)
from .serializers import (
    EpsTransactionSerializer, 
    EpsPaymentInitSerializer,
    EpsConfigurationSerializer
)

import requests

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def test_eps_validation(request):
    """
    Test EPS payment validation without actually creating payment
    """
    try:
        logger.info(f"EPS Test Validation Request: {request.data}")
        
        serializer = EpsPaymentInitSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': serializer.errors,
                'test_mode': True
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': True,
            'message': 'Validation passed',
            'validated_data': serializer.validated_data,
            'test_mode': True
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"EPS test validation error: {str(e)}")
        return Response({
            'success': False,
            'message': f'Test validation error: {str(e)}',
            'test_mode': True
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])  # You may want to change this based on your auth requirements
def initialize_eps_payment(request):
    """
    Initialize EPS payment and get redirect URL
    """
    try:
        # Log incoming request data for debugging
        logger.info(f"EPS Payment Request Data: {request.data}")
        
        serializer = EpsPaymentInitSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"EPS Validation Errors: {serializer.errors}")
            return Response({
                'success': False,
                'message': 'Invalid payment data',
                'errors': serializer.errors,
                'details': f'Failed validation for fields: {list(serializer.errors.keys())}'
            }, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        logger.info(f"EPS Validated Data: {validated_data}")
        
        # Get EPS configuration and token
        try:
            eps_config = get_eps_configuration()
        except Exception as config_error:
            logger.error(f"EPS Configuration Error: {config_error}")
            return Response({
                'success': False,
                'message': 'EPS configuration error. Please check admin panel settings.',
                'details': str(config_error)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        token = get_eps_token()
        
        if not eps_config.merchant_id or not eps_config.store_id:
            return Response({
                'success': False,
                'message': 'EPS merchant configuration incomplete. Please configure Merchant ID and Store ID in admin panel.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Generate unique transaction ID
        merchant_transaction_id = generate_merchant_transaction_id()
        
        # Generate x-hash for this transaction
        x_hash = generate_eps_hash(merchant_transaction_id, eps_config.hash_key)

        # Get callback URLs
        callback_urls = get_callback_urls(request, eps_config)

        # Prepare payment payload
        payment_payload = {
            "storeId": eps_config.store_id,
            "merchantTransactionId": merchant_transaction_id,
            "CustomerOrderId": str(validated_data['order_id']),
            "transactionTypeId": 1,  # 1 = Web
            "financialEntityId": 0,
            "transitionStatusId": 0,
            "totalAmount": str(validated_data['amount']),
            "ipAddress": get_client_ip(request),
            "version": "1",
            "successUrl": callback_urls['success_url'],
            "failUrl": callback_urls['fail_url'],
            "cancelUrl": callback_urls['cancel_url'],
            
            # Customer information
            "customerName": validated_data['customer_name'],
            "customerEmail": validated_data['customer_email'],
            "customerAddress": validated_data.get('customer_address', 'Dhaka, Bangladesh'),
            "customerAddress2": validated_data.get('customer_address2', ''),
            "customerCity": validated_data.get('customer_city', 'Dhaka'),
            "customerState": validated_data.get('customer_state', 'Dhaka'),
            "customerPostcode": validated_data.get('customer_postcode', '1000'),
            "customerCountry": validated_data.get('customer_country', 'BD'),
            "customerPhone": validated_data['customer_phone'],
            
            # Shipment information
            "shipmentName": validated_data['customer_name'],
            "shipmentAddress": validated_data.get('customer_address', 'Dhaka, Bangladesh'),
            "shipmentAddress2": validated_data.get('customer_address2', ''),
            "shipmentCity": validated_data.get('customer_city', 'Dhaka'),
            "shipmentState": validated_data.get('customer_state', 'Dhaka'),
            "shipmentPostcode": validated_data.get('customer_postcode', '1000'),
            "shipmentCountry": validated_data.get('customer_country', 'BD'),
            
            # Additional fields
            "valueA": "",
            "valueB": "",
            "valueC": "",
            "valueD": "",
            "shippingMethod": "NO",
            "noOfItem": "1",
            "productName": validated_data.get('product_name', 'Digital Product'),
            "productProfile": "general",
            "productCategory": validated_data.get('product_category', 'Digital'),
            
            # Product list
            "ProductList": [
                {
                    "ProductName": validated_data.get('product_name', 'Digital Product'),
                    "NoOfItem": "1",
                    "ProductProfile": "general",
                    "ProductCategory": validated_data.get('product_category', 'Digital'),
                    "ProductPrice": str(validated_data['amount'])
                }
            ]
        }

        logger.info(f'Initializing EPS payment for amount: {validated_data["amount"]}')
        logger.info(f'Merchant Transaction ID: {merchant_transaction_id}')

        # Make API call to initialize payment
        response = requests.post(
            f"{eps_config.base_url}/EPSEngine/InitializeEPS",
            json=payment_payload,
            headers={
                'x-hash': x_hash,
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            },
            timeout=30
        )
        
        response.raise_for_status()
        response_data = response.json()
        
        logger.info('EPS Initialize Payment Response:', response_data)
        
        transaction_id = response_data.get('TransactionId')
        redirect_url = response_data.get('RedirectURL')
        error_message = response_data.get('ErrorMessage')
        error_code = response_data.get('ErrorCode')

        if error_code or error_message:
            return Response({
                'success': False,
                'message': f"EPS Payment Error: {error_message or 'Unknown error'} (Code: {error_code})"
            }, status=status.HTTP_400_BAD_REQUEST)

        if not transaction_id or not redirect_url:
            return Response({
                'success': False,
                'message': 'Invalid response from EPS: Missing TransactionId or RedirectURL'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Create transaction record
        transaction = EpsTransaction.objects.create(
            merchant_transaction_id=merchant_transaction_id,
            eps_transaction_id=transaction_id,
            customer_order_id=str(validated_data['order_id']),
            amount=validated_data['amount'],
            customer_name=validated_data['customer_name'],
            customer_email=validated_data['customer_email'],
            customer_phone=validated_data['customer_phone'],
            customer_address=validated_data.get('customer_address', 'Dhaka, Bangladesh'),
            customer_city=validated_data.get('customer_city', 'Dhaka'),
            customer_state=validated_data.get('customer_state', 'Dhaka'),
            customer_postcode=validated_data.get('customer_postcode', '1000'),
            customer_country=validated_data.get('customer_country', 'BD'),
            product_name=validated_data.get('product_name', 'Digital Product'),
            product_category=validated_data.get('product_category', 'Digital'),
            redirect_url=redirect_url,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            user=request.user if request.user.is_authenticated else None,
            status='processing'
        )

        logger.info('✅ EPS payment initialized successfully')
        logger.info(f'Transaction ID: {transaction_id}')

        return Response({
            'success': True,
            'transaction_id': transaction_id,
            'merchant_transaction_id': merchant_transaction_id,
            'redirect_url': redirect_url,
            'gateway': 'eps'
        })

    except requests.RequestException as e:
        logger.error(f"❌ EPS payment initialization error: {str(e)}")
        
        if hasattr(e, 'response') and e.response is not None:
            if e.response.status_code == 401:
                message = 'EPS Authentication failed. Token may be expired.'
            elif e.response.status_code == 400:
                message = 'EPS Payment request invalid. Please check configuration.'
            else:
                message = f'EPS API error: {e.response.status_code}'
        else:
            message = 'Cannot connect to EPS API. Please check network connection.'
        
        return Response({
            'success': False,
            'message': message
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        return Response({
            'success': False,
            'message': 'An unexpected error occurred. Please try again.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def verify_eps_transaction(request, merchant_transaction_id):
    """
    Verify EPS transaction status
    """
    try:
        # Get EPS configuration and token
        eps_config = get_eps_configuration()
        token = get_eps_token()

        # Generate x-hash for verification
        x_hash = generate_eps_hash(merchant_transaction_id, eps_config.hash_key)

        logger.info(f'Verifying EPS transaction: {merchant_transaction_id}')

        # Make API call to verify transaction
        response = requests.get(
            f"{eps_config.base_url}/EPSEngine/CheckMerchantTransactionStatus",
            params={'merchantTransactionId': merchant_transaction_id},
            headers={
                'x-hash': x_hash,
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            },
            timeout=30
        )

        response.raise_for_status()
        transaction_data = response.json()

        if transaction_data.get('ErrorCode') or transaction_data.get('ErrorMessage'):
            return Response({
                'success': False,
                'message': f"EPS Verification Error: {transaction_data.get('ErrorMessage', 'Unknown error')} (Code: {transaction_data.get('ErrorCode')})"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Update local transaction record
        try:
            transaction = EpsTransaction.objects.get(merchant_transaction_id=merchant_transaction_id)
            transaction.payment_status = transaction_data.get('Status', '')
            transaction.financial_entity_name = transaction_data.get('FinancialEntity', '')
            transaction.is_verified = True
            transaction.verification_attempts += 1
            transaction.last_verification_at = timezone.now()
            
            # Update status based on EPS response
            eps_status = transaction_data.get('Status', '').lower()
            if eps_status in ['success', 'completed']:
                transaction.status = 'completed'
                transaction.completed_at = timezone.now()
            elif eps_status in ['failed', 'fail']:
                transaction.status = 'failed'
            elif eps_status in ['cancelled', 'cancel']:
                transaction.status = 'cancelled'
            
            transaction.save()
            
        except EpsTransaction.DoesNotExist:
            logger.warning(f'Transaction not found in local database: {merchant_transaction_id}')

        logger.info('✅ EPS transaction verified')
        logger.info(f'Status: {transaction_data.get("Status")}')

        return Response({
            'success': True,
            'status': transaction_data.get('Status'),
            'merchant_transaction_id': transaction_data.get('MerchantTransactionId'),
            'total_amount': transaction_data.get('TotalAmount'),
            'transaction_date': transaction_data.get('TransactionDate'),
            'transaction_type': transaction_data.get('TransactionType'),
            'financial_entity': transaction_data.get('FinancialEntity'),
            'customer_info': {
                'id': transaction_data.get('CustomerId'),
                'name': transaction_data.get('CustomerName'),
                'email': transaction_data.get('CustomerEmail'),
                'phone': transaction_data.get('CustomerPhone'),
                'address': transaction_data.get('CustomerAddress')
            },
            'gateway': 'eps'
        })

    except requests.RequestException as e:
        logger.error(f"❌ EPS transaction verification error: {str(e)}")
        
        if hasattr(e, 'response') and e.response is not None and e.response.status_code == 404:
            message = 'Transaction not found in EPS system'
        else:
            message = 'Error connecting to EPS API for verification'
        
        return Response({
            'success': False,
            'message': message
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        logger.error(f"❌ Unexpected verification error: {str(e)}")
        return Response({
            'success': False,
            'message': 'An unexpected error occurred during verification.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def eps_payment_callback(request):
    """
    Handle EPS payment callback
    """
    try:
        # Log the webhook
        webhook_log = EpsWebhookLog.objects.create(
            method=request.method,
            url=request.build_absolute_uri(),
            headers=dict(request.headers),
            body=request.body.decode('utf-8') if request.body else '',
            query_params=dict(request.GET),
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        # Extract callback data
        if request.method == 'POST':
            try:
                callback_data = json.loads(request.body)
            except json.JSONDecodeError:
                callback_data = dict(request.POST)
        else:
            callback_data = dict(request.GET)

        logger.info(f'EPS Callback received: {callback_data}')

        # Extract relevant data - handle both dict and QueryDict values
        def get_param_value(data, key1, key2='', default=''):
            """Helper to get parameter value from either dict or QueryDict"""
            value = data.get(key1, data.get(key2, default))
            # Handle QueryDict values (which are lists)
            if isinstance(value, list):
                return value[0] if value else default
            return value

        status_param = get_param_value(callback_data, 'status', 'Status', '').lower()
        merchant_transaction_id = get_param_value(callback_data, 'merchantTransactionId', 'MerchantTransactionId', '')
        amount = get_param_value(callback_data, 'amount', 'Amount', '')
        transaction_id = get_param_value(callback_data, 'transactionId', 'EPSTransactionId', '')
        error_code = get_param_value(callback_data, 'ErrorCode', '', '')
        error_message = get_param_value(callback_data, 'ErrorMessage', '', '')

        logger.info(f'EPS Callback - Status: {status_param}, Transaction: {merchant_transaction_id}, Error: {error_code} - {error_message}')

        # Update webhook log with processing status
        webhook_log.response_status = 200
        webhook_log.is_processed = True

        # Find and update transaction
        transaction = None
        order = None
        verification_success = False  # Initialize here for scope
        
        if merchant_transaction_id:
            try:
                transaction = EpsTransaction.objects.get(merchant_transaction_id=merchant_transaction_id)
                webhook_log.transaction = transaction
                
                # Try to find related order/purchase in your main app
                order = None
                user_package = None
                order_type = None
                
                try:
                    # Determine order type from transaction record
                    if transaction and hasattr(transaction, 'order_type'):
                        order_type = transaction.order_type
                        logger.info(f'🔍 Order type from transaction: {order_type}')
                    else:
                        # Fallback: detect from order ID format
                        if transaction and transaction.customer_order_id:
                            if transaction.customer_order_id.startswith('PKG-'):
                                order_type = 'package'
                            else:
                                order_type = 'file'
                            logger.info(f'� Order type detected from order_id: {order_type}')
                    
                    # Handle based on order type
                    if order_type == 'package':
                        # Package purchase - find UserPackage
                        from packages.models import UserPackage
                        logger.info(f'📦 Looking for package purchase with TRX: {merchant_transaction_id}')
                        
                        # First try exact TRX match
                        user_package = UserPackage.objects.filter(
                            transaction_id=merchant_transaction_id
                        ).first()
                        
                        if user_package:
                            logger.info(f'✅ Found UserPackage by exact TRX match: {user_package.id}')
                        else:
                            # Try extracting package ID from order_id (format: PKG-{id})
                            if transaction and transaction.customer_order_id:
                                try:
                                    package_id = transaction.customer_order_id.replace('PKG-', '')
                                    user_package = UserPackage.objects.filter(
                                        id=package_id,
                                        status='pending'
                                    ).order_by('-created_at').first()
                                    
                                    if user_package:
                                        # Update with correct transaction ID
                                        user_package.transaction_id = merchant_transaction_id
                                        user_package.save()
                                        logger.info(f'✅ Found UserPackage by ID, updated TRX: {user_package.id}')
                                except Exception as pkg_error:
                                    logger.error(f'Error extracting package ID: {str(pkg_error)}')
                    
                    elif order_type == 'file':
                        # File purchase - find Purchases record
                        from others.models import Purchases
                        logger.info(f'📄 Looking for file purchase with TRX: {merchant_transaction_id}')
                        
                        # First, try exact match by transaction ID
                        order = Purchases.objects.filter(trx_number=merchant_transaction_id).first()
                        
                        if order:
                            logger.info(f'✅ Found Purchases by exact TRX match: {order.id}')
                        else:
                            # Try to extract purchase ID from order ID (format: ORD-{purchase_id}-{user_id})
                            if transaction and transaction.customer_order_id:
                                order_id_parts = transaction.customer_order_id.split('-')
                                if len(order_id_parts) >= 2 and order_id_parts[0] == 'ORD':
                                    try:
                                        purchase_id = int(order_id_parts[1])
                                        order = Purchases.objects.filter(id=purchase_id, payment_status='pending').first()
                                        if order:
                                            # Update the purchase with the correct transaction ID
                                            order.trx_number = merchant_transaction_id
                                            order.save()
                                            logger.info(f'✅ Found Purchases by Order ID extraction: {order.id}, updated TRX')
                                    except (ValueError, IndexError) as e:
                                        logger.warning(f'Could not parse purchase ID from order ID: {str(e)}')
                            
                            # Last resort: find by timestamp and amount matching
                            if not order:
                                parts = merchant_transaction_id.split('-')
                                if len(parts) >= 2:
                                    try:
                                        timestamp_str = parts[1]
                                        
                                        transaction_timestamp = datetime.fromtimestamp(int(timestamp_str), tz=timezone.utc)
                                        time_window_start = transaction_timestamp - timedelta(seconds=5)
                                        time_window_end = transaction_timestamp + timedelta(seconds=5)
                                        
                                        if transaction.customer_email and transaction.customer_email != 'customer@example.com':
                                            from users.models import Users
                                            user = Users.objects.filter(email=transaction.customer_email).first()
                                            if user:
                                                order = Purchases.objects.filter(
                                                    user=user,
                                                    amount=transaction.amount,
                                                    payment_status='pending',
                                                    created_at__gte=time_window_start,
                                                    created_at__lte=time_window_end
                                                ).order_by('-created_at').first()
                                                
                                                if order:
                                                    order.trx_number = merchant_transaction_id
                                                    order.save()
                                                    logger.info(f'✅ Found Purchases by timestamp match: {order.id}, updated TRX')
                                    except (ValueError, IndexError) as e:
                                        logger.warning(f'Could not parse timestamp from transaction ID: {str(e)}')
                    
                    # Log results
                    if not order and not user_package:
                        logger.warning(f'⚠️ No order or package found for TRX: {merchant_transaction_id}, order_type: {order_type}')
                        
                except Exception as e:
                    logger.error(f'❌ Error finding purchase/package: {str(e)}', exc_info=True)
                    order = None
                    user_package = None
                
                # Update transaction based on callback
                transaction.callback_data = callback_data
                
                # Initialize payment status variables
                payment_status = 'failed'
                order_status = 'failed'
                verification_success = False
                
                if status_param in ['success', 'completed']:
                    # Verify transaction with EPS API for successful payments
                    logger.info(f'Verifying EPS transaction: {merchant_transaction_id}')
                    try:
                        # Import and use the verification function
                        from .utils import get_eps_token, get_eps_configuration, generate_eps_hash
                        
                        eps_config = get_eps_configuration()
                        token = get_eps_token()
                        x_hash = generate_eps_hash(merchant_transaction_id, eps_config.hash_key)
                        
                        # Make verification API call
                        verification_response = requests.get(
                            f"{eps_config.base_url}/EPSEngine/CheckMerchantTransactionStatus",
                            params={'merchantTransactionId': merchant_transaction_id},
                            headers={
                                'x-hash': x_hash,
                                'Authorization': f'Bearer {token}',
                                'Content-Type': 'application/json',
                            },
                            timeout=30
                        )
                        
                        verification_response.raise_for_status()
                        verification_data = verification_response.json()
                        
                        logger.info(f'EPS Verification Response: {verification_data}')
                        
                        eps_status = verification_data.get('Status', '').lower()
                        if eps_status == 'success' and not verification_data.get('ErrorCode'):
                            verification_success = True
                            payment_status = 'completed'
                            order_status = 'confirmed'
                            
                            transaction.status = 'completed'
                            transaction.payment_status = 'success'
                            transaction.completed_at = timezone.now()
                            transaction.is_verified = True
                            
                            logger.info('✅ EPS payment verified and completed')
                            
                            # Log what we're looking for
                            logger.info(f'📊 Callback Summary:')
                            logger.info(f'  - Merchant TRX ID: {merchant_transaction_id}')
                            logger.info(f'  - Customer Order ID: {transaction.customer_order_id if transaction else "N/A"}')
                            logger.info(f'  - Order Type: {order_type}')
                            logger.info(f'  - Customer Email: {transaction.customer_email if transaction else "N/A"}')
                            logger.info(f'  - Found Order: {order.id if order else "None"}')
                            logger.info(f'  - Found UserPackage: {user_package.id if user_package else "None"}')
                            
                            # If no order/package found for file purchase, try harder to find it
                            if order_type == 'file' and not order:
                                logger.warning(f'⚠️ File purchase not found, attempting deeper search...')
                                from others.models import Purchases
                                
                                # Try finding ANY pending purchase with matching order_id in the trx_number
                                if transaction and transaction.customer_order_id:
                                    # Extract purchase ID from order ID (ORD-{id}-{user_id})
                                    try:
                                        order_id_parts = transaction.customer_order_id.split('-')
                                        if len(order_id_parts) >= 2:
                                            purchase_id = int(order_id_parts[1])
                                            logger.info(f'🔍 Extracted purchase_id from order_id: {purchase_id}')
                                            
                                            # Find by purchase ID directly
                                            order = Purchases.objects.filter(
                                                id=purchase_id,
                                                payment_status='pending'
                                            ).first()
                                            
                                            if order:
                                                # Update with correct transaction ID
                                                order.trx_number = merchant_transaction_id
                                                order.save()
                                                logger.info(f'✅ Found purchase by ID extraction: {order.id}')
                                    except (ValueError, IndexError, Exception) as e:
                                        logger.error(f'Could not extract purchase ID: {str(e)}')
                            
                            # Update order status if order exists (file purchase)
                            if order:
                                order.payment_status = 'completed'
                                order.status = True  # Set to active (BooleanField)
                                order.save()
                                logger.info(f'✅ File purchase {order.id} status updated to completed/active')
                                
                            # Activate package if package purchase exists
                            if user_package:
                                try:
                                    logger.info(f"📦 Activating package purchase, user_package_id: {user_package.id}")
                                    
                                    # Import and activate package
                                    from packages.views import activate_package_after_payment
                                    package_activated = activate_package_after_payment(
                                        user_package_id=user_package.id,
                                        transaction_data={
                                            'status': status_param,
                                            'merchantTransactionId': merchant_transaction_id,
                                            'amount': amount,
                                            'transactionId': transaction_id,
                                            'timestamp': timezone.now().isoformat(),
                                            'eps_verification': verification_data
                                        }
                                    )
                                    
                                    if package_activated:
                                        logger.info(f'✅ Package activated successfully for user_package_id: {user_package.id}')
                                    else:
                                        logger.error(f'❌ Failed to activate package for user_package_id: {user_package.id}')
                                except Exception as pkg_error:
                                    logger.error(f'❌ Error activating package: {str(pkg_error)}')
                            
                            # Warn if neither order nor package found
                            if not order and not user_package:
                                logger.warning(f'⚠️ Payment completed but no file purchase or package found for TRX: {merchant_transaction_id}')
                        else:
                            logger.warning(f'⚠️ EPS verification failed or status not Success: {eps_status}')
                            verification_success = False
                            payment_status = 'failed'
                            order_status = 'failed'
                            
                            transaction.status = 'failed'
                            transaction.payment_status = 'failed'
                            
                            # Update order/package to failed status
                            if order:
                                order.payment_status = 'failed'
                                order.status = False
                                order.save()
                                logger.info(f'✅ File purchase {order.id} marked as failed (verification failed)')
                            
                            if user_package:
                                user_package.status = 'failed'
                                user_package.save()
                                logger.info(f'✅ Package purchase {user_package.id} marked as failed (verification failed)')
                            
                    except Exception as verification_error:
                        logger.error(f'EPS verification error: {str(verification_error)}')
                        verification_success = False
                        payment_status = 'failed'
                        order_status = 'failed'
                        
                        transaction.status = 'failed'
                        transaction.payment_status = 'failed'
                        
                        # Update order/package to failed status
                        if order:
                            order.payment_status = 'failed'
                            order.status = False
                            order.save()
                            logger.info(f'✅ File purchase {order.id} marked as failed (verification error)')
                        
                        if user_package:
                            user_package.status = 'failed'
                            user_package.save()
                            logger.info(f'✅ Package purchase {user_package.id} marked as failed (verification error)')
                        
                elif status_param in ['cancel', 'cancelled']:
                    payment_status = 'cancelled'
                    order_status = 'cancelled'
                    transaction.status = 'cancelled'
                    transaction.payment_status = 'cancelled'
                    logger.info('EPS payment cancelled by user')
                    
                    # Update order if exists (file purchase)
                    if order:
                        order.payment_status = 'cancelled'
                        order.status = False  # Set to inactive (BooleanField)
                        order.save()
                        logger.info(f'✅ File purchase {order.id} marked as cancelled')
                    
                    # Update package if exists (package purchase)
                    if user_package:
                        user_package.status = 'cancelled'
                        user_package.save()
                        logger.info(f'✅ Package purchase {user_package.id} marked as cancelled')
                        
                else:
                    # Failed status
                    payment_status = 'failed'
                    order_status = 'failed'
                    transaction.status = 'failed'
                    transaction.payment_status = 'failed'
                    logger.info(f'EPS payment failed: {status_param}')
                    
                    # Update order if exists (file purchase)
                    if order:
                        order.payment_status = 'failed'
                        order.status = False  # Set to inactive (BooleanField)
                        order.save()
                        logger.info(f'✅ File purchase {order.id} marked as failed')
                    
                    # Update package if exists (package purchase)
                    if user_package:
                        user_package.status = 'failed'
                        user_package.save()
                        logger.info(f'✅ Package purchase {user_package.id} marked as failed')
                
                # Store error information if present
                if error_code or error_message:
                    transaction.error_code = error_code
                    transaction.error_message = error_message
                
                # Store gateway response in order
                if order:
                    gateway_response = {
                        'status': status_param,
                        'merchantTransactionId': merchant_transaction_id,
                        'amount': amount,
                        'transactionId': transaction_id,
                        'timestamp': timezone.now().isoformat(),
                        'errorCode': error_code,
                        'errorMessage': error_message
                    }
                    # Assuming your order model has a field to store gateway response
                    if hasattr(order, 'gateway_response'):
                        order.gateway_response = gateway_response
                        order.save()
                
                transaction.save()
                
                logger.info(f'Transaction {merchant_transaction_id} updated with status: {status_param}')
                
            except EpsTransaction.DoesNotExist:
                logger.warning(f'Transaction not found for callback: {merchant_transaction_id}')
                webhook_log.processing_errors = f'Transaction not found: {merchant_transaction_id}'

        webhook_log.save()

        # Determine frontend redirect URLs based on environment
        base_frontend_url = 'https://bdmouza.com'
        # base_frontend_url = 'http://localhost:5173'
        
        # Redirect to appropriate frontend page based on status
        order_id = order.id if order else 'unknown'
        
        if status_param in ['success', 'completed'] and verification_success:
            redirect_url = f'{base_frontend_url}/payment/success?gateway=eps&transaction={merchant_transaction_id}'
        elif status_param in ['cancel', 'cancelled']:
            redirect_url = f'{base_frontend_url}/payment/cancelled?gateway=eps&transaction={merchant_transaction_id}'
        else:
            redirect_url = f'{base_frontend_url}/payment/failed?gateway=eps&transaction={merchant_transaction_id}&error={error_code}'

        logger.info(f'Redirecting to: {redirect_url}')

        # For API responses
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({
                'success': True,
                'status': status_param,
                'merchant_transaction_id': merchant_transaction_id,
                'redirect_url': redirect_url,
                'error_code': error_code,
                'error_message': error_message
            })

        # For browser redirects
        return redirect(redirect_url)

    except Exception as e:
        logger.error(f"❌ EPS callback error: {str(e)}")
        
        # Update webhook log with error
        if 'webhook_log' in locals():
            webhook_log.processing_errors = str(e)
            webhook_log.response_status = 500
            webhook_log.save()

        return JsonResponse({
            'success': False,
            'message': 'Callback processing failed'
        }, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_transaction_status(request, merchant_transaction_id):
    """
    Get transaction status from local database
    """
    try:
        transaction = EpsTransaction.objects.get(merchant_transaction_id=merchant_transaction_id)
        serializer = EpsTransactionSerializer(transaction)
        return Response({
            'success': True,
            'transaction': serializer.data
        })
    except EpsTransaction.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Transaction not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_eps_configuration_api(request):
    """
    Get EPS configuration (without sensitive data)
    """
    try:
        config = get_eps_configuration()
        # Return only non-sensitive configuration data
        return Response({
            'success': True,
            'config': {
                'is_active': config.is_active,
                'is_sandbox': config.is_sandbox,
                'merchant_id': config.merchant_id,
                'store_id': config.store_id,
                'base_url': config.base_url
            }
        })
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
