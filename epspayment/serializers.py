"""
EPS Payment Serializers
"""
from rest_framework import serializers
from decimal import Decimal
from .models import EpsTransaction, EpsConfiguration


class EpsPaymentInitSerializer(serializers.Serializer):
    """Serializer for initializing EPS payment"""
    
    # Order Information
    order_id = serializers.CharField(
        max_length=100,
        help_text="Unique order identifier"
    )
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        help_text="Payment amount"
    )
    
    # Customer Information (Required)
    customer_name = serializers.CharField(
        max_length=100,
        help_text="Customer full name"
    )
    customer_email = serializers.CharField(
        max_length=254,  # Standard email max length
        required=False,
        default="customer@example.com",
        allow_blank=True,
        help_text="Customer email address"
    )
    customer_phone = serializers.CharField(
        max_length=20,
        required=False,  # Make it optional
        default="01700000000",  # Provide default
        allow_blank=True,
        help_text="Customer phone number"
    )
    
    # Customer Information (Optional)
    customer_address = serializers.CharField(
        max_length=500,
        required=False,
        default="Dhaka, Bangladesh",
        allow_blank=True,
        help_text="Customer address"
    )
    customer_address2 = serializers.CharField(
        max_length=500,
        required=False,
        default="",
        allow_blank=True,
        help_text="Customer address line 2"
    )
    customer_city = serializers.CharField(
        max_length=50,
        required=False,
        default="Dhaka",
        allow_blank=True,
        help_text="Customer city"
    )
    customer_state = serializers.CharField(
        max_length=50,
        required=False,
        default="Dhaka",
        allow_blank=True,
        help_text="Customer state/province"
    )
    customer_postcode = serializers.CharField(
        max_length=10,
        required=False,
        default="1000",
        allow_blank=True,
        help_text="Customer postal code"
    )
    customer_country = serializers.CharField(
        max_length=2,
        required=False,
        default="BD",
        allow_blank=True,
        help_text="Customer country code (2 letters)"
    )
    
    # Product Information (Optional)
    product_name = serializers.CharField(
        max_length=255,
        required=False,
        default="Digital Product",
        allow_blank=True,
        help_text="Product name"
    )
    product_category = serializers.CharField(
        max_length=100,
        required=False,
        default="Digital",
        allow_blank=True,
        help_text="Product category"
    )
    
    def validate_amount(self, value):
        """Validate payment amount"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value
    
    def validate_customer_email(self, value):
        """Validate customer email"""
        import re
        
        # If empty or blank, use default
        if not value or value.strip() == '':
            return "customer@example.com"
        
        # Basic email regex validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            # If invalid email format, use default
            return "customer@example.com"
        
        return value
    
    def validate_customer_phone(self, value):
        """Validate customer phone number"""
        # If empty, use default
        if not value or value.strip() == '':
            return "01700000000"
        
        # Remove any non-digit characters for validation
        phone_digits = ''.join(filter(str.isdigit, value))
        
        if len(phone_digits) < 10:
            # If less than 10 digits, use default
            return "01700000000"
        
        return value
    
    def validate_customer_country(self, value):
        """Validate country code"""
        if len(value) != 2:
            raise serializers.ValidationError("Country code must be 2 characters")
        return value.upper()


class EpsTransactionSerializer(serializers.ModelSerializer):
    """Serializer for EPS Transaction model"""
    
    is_successful = serializers.SerializerMethodField()
    can_be_refunded = serializers.SerializerMethodField()
    
    class Meta:
        model = EpsTransaction
        fields = [
            'id',
            'merchant_transaction_id',
            'eps_transaction_id',
            'customer_order_id',
            'amount',
            'currency',
            'status',
            'payment_status',
            'customer_name',
            'customer_email',
            'customer_phone',
            'customer_address',
            'customer_city',
            'customer_state',
            'customer_postcode',
            'customer_country',
            'product_name',
            'product_category',
            'no_of_items',
            'redirect_url',
            'is_verified',
            'verification_attempts',
            'last_verification_at',
            'financial_entity_name',
            'created_at',
            'updated_at',
            'completed_at',
            'is_successful',
            'can_be_refunded'
        ]
        read_only_fields = [
            'id',
            'merchant_transaction_id',
            'eps_transaction_id',
            'redirect_url',
            'is_verified',
            'verification_attempts',
            'last_verification_at',
            'created_at',
            'updated_at',
            'completed_at',
            'is_successful',
            'can_be_refunded'
        ]
    
    def get_is_successful(self, obj):
        """Check if transaction is successful"""
        return obj.is_successful()
    
    def get_can_be_refunded(self, obj):
        """Check if transaction can be refunded"""
        return obj.can_be_refunded()


class EpsTransactionListSerializer(serializers.ModelSerializer):
    """Simplified serializer for transaction listing"""
    
    is_successful = serializers.SerializerMethodField()
    
    class Meta:
        model = EpsTransaction
        fields = [
            'id',
            'merchant_transaction_id',
            'eps_transaction_id',
            'customer_order_id',
            'amount',
            'currency',
            'status',
            'payment_status',
            'customer_name',
            'customer_email',
            'created_at',
            'completed_at',
            'is_successful'
        ]
    
    def get_is_successful(self, obj):
        """Check if transaction is successful"""
        return obj.is_successful()


class EpsConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for EPS Configuration (Admin use)"""
    
    class Meta:
        model = EpsConfiguration
        fields = [
            'id',
            'base_url',
            'username',
            'password',
            'hash_key',
            'merchant_id',
            'store_id',
            'is_active',
            'is_sandbox',
            'success_url',
            'fail_url',
            'cancel_url',
            'created_at',
            'updated_at'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'hash_key': {'write_only': True}
        }
    
    def validate_base_url(self, value):
        """Validate base URL format"""
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("Base URL must start with http:// or https://")
        return value
    
    def validate(self, data):
        """Validate EPS configuration"""
        # Ensure all required fields are provided
        required_fields = ['base_url', 'username', 'password', 'hash_key', 'merchant_id', 'store_id']
        for field in required_fields:
            if not data.get(field):
                raise serializers.ValidationError(f"{field} is required")
        
        return data


class EpsConfigurationPublicSerializer(serializers.ModelSerializer):
    """Public serializer for EPS Configuration (excludes sensitive data)"""
    
    class Meta:
        model = EpsConfiguration
        fields = [
            'id',
            'base_url',
            'merchant_id',
            'store_id',
            'is_active',
            'is_sandbox',
            'created_at',
            'updated_at'
        ]


class EpsCallbackSerializer(serializers.Serializer):
    """Serializer for EPS payment callback data"""
    
    status = serializers.CharField(
        max_length=20,
        help_text="Payment status (success, fail, cancel)"
    )
    merchantTransactionId = serializers.CharField(
        max_length=100,
        required=False,
        help_text="Merchant transaction ID"
    )
    transactionId = serializers.CharField(
        max_length=100,
        required=False,
        help_text="EPS transaction ID"
    )
    amount = serializers.CharField(
        max_length=20,
        required=False,
        help_text="Transaction amount"
    )
    
    def validate_status(self, value):
        """Validate callback status"""
        allowed_statuses = ['success', 'fail', 'cancel']
        if value.lower() not in allowed_statuses:
            raise serializers.ValidationError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return value.lower()


class EpsVerificationSerializer(serializers.Serializer):
    """Serializer for EPS transaction verification response"""
    
    success = serializers.BooleanField()
    status = serializers.CharField(max_length=50, required=False)
    merchant_transaction_id = serializers.CharField(max_length=100, required=False)
    total_amount = serializers.CharField(max_length=20, required=False)
    transaction_date = serializers.CharField(max_length=50, required=False)
    transaction_type = serializers.CharField(max_length=50, required=False)
    financial_entity = serializers.CharField(max_length=100, required=False)
    customer_info = serializers.DictField(required=False)
    gateway = serializers.CharField(max_length=20, default='eps')


class EpsPaymentResponseSerializer(serializers.Serializer):
    """Serializer for EPS payment initialization response"""
    
    success = serializers.BooleanField()
    transaction_id = serializers.CharField(max_length=100, required=False)
    merchant_transaction_id = serializers.CharField(max_length=100, required=False)
    redirect_url = serializers.URLField(required=False)
    gateway = serializers.CharField(max_length=20, default='eps')
    message = serializers.CharField(max_length=500, required=False)
    errors = serializers.DictField(required=False)