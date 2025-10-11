"""
EPS Payment Gateway Utility Functions
"""
import hashlib
import hmac
import base64
import requests
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from .models import EpsConfiguration, EpsTokenCache
import logging

logger = logging.getLogger(__name__)


def generate_eps_hash(data: str, hash_key: str) -> str:
    """
    Generate x-hash for EPS API authentication

    Args:
        data (str): Data to hash
        hash_key (str): Hash key from EPS configuration

    Returns:
        str: Base64 encoded HMAC-SHA512 hash
    """
    return base64.b64encode(
        hmac.new(
            hash_key.encode("utf-8"),  # secret key
            data.encode("utf-8"),      # data/message
            hashlib.sha512             # hashing algorithm
        ).digest()
    ).decode("utf-8")


def get_eps_configuration():
    """
    Get active EPS configuration
    
    Returns:
        EpsConfiguration: Active EPS configuration object
        
    Raises:
        Exception: If no active configuration is found
    """
    try:
        config = EpsConfiguration.objects.filter(is_active=True).first()
        if not config:
            raise Exception("No active EPS configuration found. Please configure EPS settings in admin panel.")
        return config
    except EpsConfiguration.DoesNotExist:
        raise Exception("EPS configuration not found. Please configure EPS settings in admin panel.")


def get_cached_token(key='eps_token'):
    """
    Get cached token from database
    
    Args:
        key (str): Cache key
        
    Returns:
        str or None: Cached token value if valid, None otherwise
    """
    try:
        cache_entry = EpsTokenCache.objects.filter(key=key).first()
        if cache_entry and not cache_entry.is_expired():
            logger.info(f"Using cached EPS token for key: {key}")
            return cache_entry.value
        elif cache_entry:
            # Token expired, delete it
            cache_entry.delete()
            logger.info(f"Expired token deleted for key: {key}")
    except Exception as e:
        logger.warning(f"Error retrieving cached token: {str(e)}")
    
    return None


def set_cached_token(key, value, expiry_seconds):
    """
    Set cached token in database
    
    Args:
        key (str): Cache key
        value (str): Token value
        expiry_seconds (int): Expiry time in seconds
    """
    try:
        expires_at = timezone.now() + timedelta(seconds=expiry_seconds)
        
        # Update or create cache entry
        cache_entry, created = EpsTokenCache.objects.update_or_create(
            key=key,
            defaults={
                'value': value,
                'expires_at': expires_at
            }
        )
        
        action = "created" if created else "updated"
        logger.info(f"Token cache {action} for key: {key}, expires at: {expires_at}")
        
    except Exception as e:
        logger.error(f"Error caching token: {str(e)}")


def clear_cached_token(key='eps_token'):
    """
    Clear cached token from database
    
    Args:
        key (str): Cache key
    """
    try:
        deleted_count = EpsTokenCache.objects.filter(key=key).delete()[0]
        if deleted_count > 0:
            logger.info(f"Cleared cached token for key: {key}")
        else:
            logger.info(f"No cached token found for key: {key}")
    except Exception as e:
        logger.warning(f"Error clearing cached token: {str(e)}")


def get_eps_token():
    """
    Get EPS authentication token with caching
    
    Returns:
        str: EPS Bearer token
        
    Raises:
        Exception: If token retrieval fails
    """
    try:
        # Check for cached token
        # cached_token = get_cached_token('eps_token')
        # if cached_token:
        #     return cached_token

        # Get EPS configuration
        eps_config = get_eps_configuration()
        
        if not eps_config.username or not eps_config.password or not eps_config.hash_key:
            raise Exception('EPS configuration incomplete. Please configure username, password, and hash key.')

        # Generate x-hash using username
        x_hash = generate_eps_hash(eps_config.username, eps_config.hash_key)

        logger.info("Requesting new EPS token from API...")
        print("🧪 Requesting new EPS token from API...")
        print(f"EPS Base URL: {eps_config.base_url}")
        print(f"EPS Username: {eps_config.username}")
        print(f"EPS Hash Key: {eps_config.hash_key}")
        print(f"EPS x-hash: {x_hash}")
        # Make API call to get token
        response = requests.post(
            f"{eps_config.base_url}/Auth/GetToken",
            json={
                "userName": eps_config.username,
                "password": eps_config.password,
            },
            headers={
                'x-hash': x_hash,
                'Content-Type': 'application/json',
            },
            timeout=30
        )
        
        response.raise_for_status()
        response_data = response.json()
        print("🧪 EPS Token Response:", response_data)
        logger.info('EPS Token Response:', response_data)
        
        token = response_data.get('token')
        expire_date = response_data.get('expireDate')
        error_message = response_data.get('errorMessage')
        error_code = response_data.get('errorCode')
        print("🧪 EPS Token data ")
        print(token, expire_date, error_message, error_code)
        if error_code or error_message:
            raise Exception(f"EPS Token Error: {error_message or 'Unknown error'} (Code: {error_code})")

        if not token:
            raise Exception('No token received from EPS API')

        # Calculate expiry time (expire 5 minutes before actual expiry)
        if expire_date:
            try:
                # Handle EPS datetime format with high precision microseconds
                # First, replace 'Z' with '+00:00' for timezone
                expire_date_str = expire_date.replace('Z', '+00:00')
                
                # If there are more than 6 decimal places in microseconds, truncate to 6
                if '.' in expire_date_str:
                    date_part, time_part = expire_date_str.split('T')
                    if '+' in time_part:
                        time_only, tz_part = time_part.split('+')
                        if '.' in time_only:
                            time_base, microseconds = time_only.split('.')
                            # Truncate microseconds to 6 digits
                            microseconds = microseconds[:6].ljust(6, '0')
                            expire_date_str = f"{date_part}T{time_base}.{microseconds}+{tz_part}"
                
                expiry_date = datetime.fromisoformat(expire_date_str)
                buffer_time_seconds = 5 * 60  # 5 minutes
                cache_expiry_seconds = max(300, int((expiry_date.timestamp() - datetime.now().timestamp() - buffer_time_seconds)))
            except ValueError as e:
                logger.warning(f"Failed to parse expire_date '{expire_date}': {str(e)}. Using default expiry.")
                # Default to 1 hour if parsing fails
                cache_expiry_seconds = 3600
        else:
            # Default to 1 hour if no expiry date provided
            cache_expiry_seconds = 3600

        # Cache the token
        set_cached_token('eps_token', token, cache_expiry_seconds)
        
        logger.info(f"✅ EPS token obtained and cached for {cache_expiry_seconds} seconds")
        logger.info(f"Token expires at: {expire_date}")
        
        return token

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ EPS token request error: {str(e)}")
        
        if hasattr(e, 'response') and e.response is not None:
            if e.response.status_code == 401:
                raise Exception('EPS Authentication failed. Please check username and password.')
            elif e.response.status_code == 400:
                raise Exception('EPS Token request invalid. Please check configuration.')
        
        raise Exception(f'Cannot connect to EPS API: {str(e)}')
    
    except Exception as e:
        logger.error(f"❌ EPS token error: {str(e)}")
        raise


def generate_merchant_transaction_id():
    """
    Generate unique merchant transaction ID
    
    Returns:
        str: Unique transaction ID
    """
    import uuid
    timestamp = int(datetime.now().timestamp())
    unique_id = str(uuid.uuid4())[:8]
    return f"EPS-{timestamp}-{unique_id}"


def get_client_ip(request):
    """
    Get client IP address from request
    
    Args:
        request: Django request object
        
    Returns:
        str: Client IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_callback_urls(request, eps_config=None):
    """
    Generate callback URLs for EPS payment
    
    Args:
        request: Django request object
        eps_config: EPS configuration object (optional)
        
    Returns:
        dict: Dictionary containing success, fail, cancel, and callback URLs
    """
    if eps_config is None:
        eps_config = get_eps_configuration()
    
    # Always use custom domain for all callbacks (ignore config URLs)
    base_callback_url = "https://api.bdmouza.com"
    
    # Define all callback URLs with your custom domain
    # These will always override any URLs set in EPS configuration
    success_url = f"{base_callback_url}/api/payment/eps/callback?status=success"
    fail_url = f"{base_callback_url}/api/payment/eps/callback?status=fail"
    cancel_url = f"{base_callback_url}/api/payment/eps/callback?status=cancel"
    callback_url = f"{base_callback_url}/api/payment/eps/callback"
    
    logger.info(f"🔗 Using custom callback domain: {base_callback_url}")
    
    return {
        'success_url': success_url,
        'fail_url': fail_url,
        'cancel_url': cancel_url,
        'callback_url': callback_url,
        'base_callback_url': base_callback_url
    }


def validate_eps_callback_signature(request_data, hash_key):
    """
    Validate EPS callback signature (if EPS provides signature verification)
    
    Args:
        request_data (dict): Callback request data
        hash_key (str): EPS hash key
        
    Returns:
        bool: True if signature is valid, False otherwise
    """
    # This would depend on EPS signature implementation
    # For now, return True as EPS signature validation is not clearly specified
    return True


def log_eps_request(method, url, headers=None, body=None, response=None):
    """
    Log EPS API requests for debugging
    
    Args:
        method (str): HTTP method
        url (str): Request URL
        headers (dict): Request headers
        body (str): Request body
        response (dict): Response data
    """
    logger.info(f"EPS API Request: {method} {url}")
    if headers:
        logger.debug(f"Headers: {headers}")
    if body:
        logger.debug(f"Body: {body}")
    if response:
        logger.info(f"Response: {response}")


def create_eps_payment(payment_data):
    """
    Create EPS payment for integration with existing views
    
    Args:
        payment_data (dict): Payment data containing:
            - amount (float): Payment amount
            - customer_name (str): Customer name
            - customer_email (str): Customer email
            - customer_phone (str): Customer phone
            - order_id (str): Order ID
            - description (str): Payment description
            - user_id (int): User ID (optional)
            - purchase_id (int): Purchase ID (optional)
    
    Returns:
        dict: Payment creation result
    """
    try:
        # Import here to avoid circular imports
        from .serializers import EpsPaymentInitSerializer
        from .models import EpsTransaction, EpsConfiguration
        import json
        
        # Log the input data for debugging
        logger.info(f"EPS Payment Data Received: {payment_data}")
        
        # Check if EPS configuration exists
        eps_config = EpsConfiguration.objects.filter(is_active=True).first()
        if not eps_config:
            return {
                'success': False,
                'message': 'No active EPS configuration found. Please create an EPS configuration in Django admin.'
            }
        
        # Validate required fields
        required_fields = ['amount', 'customer_name', 'customer_email', 'order_id']
        missing_fields = [field for field in required_fields if not payment_data.get(field)]
        
        if missing_fields:
            return {
                'success': False,
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }
        
        # Clean and prepare phone number
        customer_phone = str(payment_data.get('customer_phone', '01700000000'))
        # Remove any non-digit characters except +
        cleaned_phone = ''.join(filter(lambda x: x.isdigit() or x == '+', customer_phone))
        if not cleaned_phone:
            cleaned_phone = '01700000000'  # Default phone
        
        # Prepare comprehensive request data with all required and optional fields
        request_data = {
            # Required fields
            'amount': float(payment_data['amount']),
            'customer_name': str(payment_data['customer_name'])[:100],  # Limit to max length
            'customer_email': str(payment_data['customer_email']),
            'customer_phone': cleaned_phone,
            'order_id': str(payment_data['order_id'])[:100],  # Limit to max length
            
            # Optional fields with defaults
            'product_name': str(payment_data.get('description', 'Digital Service'))[:255],
            'product_category': 'Digital',
            'customer_address': 'Dhaka, Bangladesh',
            'customer_address2': '',
            'customer_city': 'Dhaka',
            'customer_state': 'Dhaka',
            'customer_postcode': '1000',
            'customer_country': 'BD',
        }
        
        logger.info(f"EPS Request Data Prepared: {request_data}")
        
        # Validate data with serializer before proceeding
        serializer = EpsPaymentInitSerializer(data=request_data)
        if not serializer.is_valid():
            logger.error(f"EPS Serializer Validation Errors: {serializer.errors}")
            return {
                'success': False,
                'message': 'Payment data validation failed',
                'errors': serializer.errors,
                'details': f'Validation failed for: {list(serializer.errors.keys())}'
            }
        
        # If validation passes, get EPS token and make actual API call
        validated_data = serializer.validated_data
        
        # Get EPS token for authentication
        try:
            eps_token = get_eps_token()
            print("🧪 EPS Token obtained for payment initialization")
            print(f"EPS Token ini: {eps_token}")
            logger.info("✅ EPS token obtained for payment initialization")
        except Exception as token_error:
            logger.error(f"Failed to get EPS token: {str(token_error)}")
            return {
                'success': False,
                'message': f'EPS authentication failed: {str(token_error)}'
            }
        
        # Generate unique transaction ID
        merchant_transaction_id = generate_merchant_transaction_id()
        
        # Generate x-hash for this transaction
        x_hash = generate_eps_hash(merchant_transaction_id, eps_config.hash_key)
        
        # Get callback URLs using the utility function
        # Note: We pass None as request since we're using hardcoded URLs
        callback_urls = get_callback_urls(None, eps_config)
        
        # Log callback URLs for debugging
        logger.info(f"🔗 EPS Callback URLs:")
        logger.info(f"  Success: {callback_urls['success_url']}")
        logger.info(f"  Fail: {callback_urls['fail_url']}")
        logger.info(f"  Cancel: {callback_urls['cancel_url']}")
        print(f"🔗 EPS Callback URLs:")
        print(f"  Success: {callback_urls['success_url']}")
        print(f"  Fail: {callback_urls['fail_url']}")
        print(f"  Cancel: {callback_urls['cancel_url']}")
        
        # Prepare EPS payment payload (matching your frontend structure)
        payment_payload = {
            "storeId": eps_config.store_id,
            "merchantTransactionId": merchant_transaction_id,
            "CustomerOrderId": validated_data['order_id'],
            "transactionTypeId": 1,  # 1 = Web
            "financialEntityId": 0,
            "transitionStatusId": 0,
            "totalAmount": str(validated_data['amount']),
            "ipAddress": "103.12.45.69",  # Default IP, can be improved
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
            # Shipment information (same as customer for digital products)
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
        
        logger.info(f"EPS Payment Payload Prepared: {payment_payload}")
        
        # Make API call to EPS
        try:
            response = requests.post(
                f"{eps_config.base_url}/EPSEngine/InitializeEPS",
                json=payment_payload,
                headers={
                    'x-hash': x_hash,
                    'Authorization': f'Bearer {eps_token}',
                    'Content-Type': 'application/json',
                },
                timeout=30
            )
            
            response.raise_for_status()
            response_data = response.json()
            print("🧪 EPS Initialize Payment Response:", response_data)
            logger.info(f"EPS Initialize Payment Response: {response_data}")
            
            transaction_id = response_data.get('TransactionId')
            redirect_url = response_data.get('RedirectURL')
            error_message = response_data.get('ErrorMessage')
            error_code = response_data.get('ErrorCode')
            
            if error_code or error_message:
                logger.error(f"EPS API Error: {error_message} (Code: {error_code})")
                return {
                    'success': False,
                    'message': f'EPS Payment Error: {error_message or "Unknown error"} (Code: {error_code})'
                }
            
            if not transaction_id or not redirect_url:
                logger.error(f"Invalid EPS response: Missing TransactionId or RedirectURL")
                return {
                    'success': False,
                    'message': 'Invalid response from EPS: Missing TransactionId or RedirectURL'
                }
            
            # Create EPS transaction record with actual response data
            eps_transaction = EpsTransaction.objects.create(
                merchant_transaction_id=merchant_transaction_id,
                eps_transaction_id=transaction_id,
                customer_order_id=validated_data['order_id'],
                order_type=payment_data.get('order_type', 'file'),  # Add order_type field
                amount=validated_data['amount'],
                currency='BDT',
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
                status='PENDING',
                payment_status='PENDING'
            )
            
            logger.info(f"✅ EPS Transaction Created: {eps_transaction.merchant_transaction_id}")
            logger.info(f"✅ EPS Transaction ID: {transaction_id}")
            logger.info(f"✅ EPS Redirect URL: {redirect_url}")
            
            return {
                'success': True,
                'payment_url': redirect_url,
                'transaction_id': merchant_transaction_id,
                'eps_transaction_id': transaction_id,
                'message': 'EPS payment initialized successfully'
            }
            
        except requests.exceptions.RequestException as api_error:
            logger.error(f"EPS API request error: {str(api_error)}")
            
            if hasattr(api_error, 'response') and api_error.response is not None:
                if api_error.response.status_code == 401:
                    return {
                        'success': False,
                        'message': 'EPS Authentication failed. Token may be expired.'
                    }
                elif api_error.response.status_code == 400:
                    return {
                        'success': False,
                        'message': 'EPS Payment request invalid. Please check configuration.'
                    }
            
            return {
                'success': False,
                'message': f'EPS API connection error: {str(api_error)}'
            }
            
    except Exception as e:
        logger.error(f"EPS payment creation error: {str(e)}", exc_info=True)
        return {
            'success': False,
            'message': f'EPS payment error: {str(e)}'
        }