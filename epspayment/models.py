from django.db import models
from django.conf import settings
import uuid


class EpsConfiguration(models.Model):
    """EPS Payment Gateway Configuration Model"""
    
    # Basic Configuration
    base_url = models.URLField(
        max_length=255,
        help_text="EPS API Base URL (e.g., https://eps.example.com)"
    )
    username = models.CharField(
        max_length=100,
        help_text="EPS API Username"
    )
    password = models.CharField(
        max_length=100,
        help_text="EPS API Password"
    )
    hash_key = models.CharField(
        max_length=255,
        help_text="EPS Hash Key for authentication"
    )
    
    # Merchant Configuration
    merchant_id = models.CharField(
        max_length=100,
        help_text="EPS Merchant ID"
    )
    store_id = models.CharField(
        max_length=100,
        help_text="EPS Store ID"
    )
    
    # Environment Settings
    is_active = models.BooleanField(
        default=True,
        help_text="Enable/Disable EPS payment gateway"
    )
    is_sandbox = models.BooleanField(
        default=True,
        help_text="Use sandbox environment for testing"
    )
    
    # Callback URLs
    success_url = models.URLField(
        max_length=255,
        blank=True,
        help_text="Success callback URL (optional - will use default)"
    )
    fail_url = models.URLField(
        max_length=255,
        blank=True,
        help_text="Failure callback URL (optional - will use default)"
    )
    cancel_url = models.URLField(
        max_length=255,
        blank=True,
        help_text="Cancel callback URL (optional - will use default)"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "EPS Configuration"
        verbose_name_plural = "EPS Configurations"
    
    def __str__(self):
        return f"EPS Config - {self.merchant_id} ({'Sandbox' if self.is_sandbox else 'Live'})"


class EpsTransaction(models.Model):
    """EPS Payment Transaction Model"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'), 
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    # Transaction Identifiers
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant_transaction_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique merchant transaction ID"
    )
    eps_transaction_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="EPS system transaction ID"
    )
    
    # Order Information
    customer_order_id = models.CharField(
        max_length=100,
        help_text="Customer's order ID"
    )
    order_type = models.CharField(
        max_length=20,
        choices=[
            ('file', 'File Purchase'),
            ('package', 'Package Purchase'),
        ],
        default='file',
        help_text="Type of purchase: file or package"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Transaction amount"
    )
    currency = models.CharField(
        max_length=3,
        default='BDT',
        help_text="Currency code"
    )
    
    # Transaction Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    payment_status = models.CharField(
        max_length=50,
        blank=True,
        help_text="EPS payment status"
    )
    
    # Customer Information
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20)
    customer_address = models.TextField()
    customer_city = models.CharField(max_length=50, default='Dhaka')
    customer_state = models.CharField(max_length=50, default='Dhaka')
    customer_postcode = models.CharField(max_length=10, default='1000')
    customer_country = models.CharField(max_length=2, default='BD')
    
    # Product Information
    product_name = models.CharField(
        max_length=255,
        default='Digital Product'
    )
    product_category = models.CharField(
        max_length=100,
        default='Digital'
    )
    no_of_items = models.IntegerField(default=1)
    
    # Payment URLs
    redirect_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="EPS redirect URL for payment"
    )
    
    # Callback Information
    callback_data = models.JSONField(
        blank=True,
        null=True,
        help_text="Raw callback data from EPS"
    )
    
    # Verification Information
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether transaction has been verified with EPS"
    )
    verification_attempts = models.IntegerField(
        default=0,
        help_text="Number of verification attempts"
    )
    last_verification_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Last verification attempt timestamp"
    )
    
    # Additional Information
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text="Customer's IP address"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="Customer's user agent"
    )
    
    # Financial Entity Information
    financial_entity_id = models.IntegerField(default=0)
    financial_entity_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Bank or financial institution name"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Transaction completion timestamp"
    )
    
    # Related User (optional)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="Associated user account"
    )
    
    class Meta:
        verbose_name = "EPS Transaction"
        verbose_name_plural = "EPS Transactions"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['merchant_transaction_id']),
            models.Index(fields=['eps_transaction_id']),
            models.Index(fields=['customer_order_id']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"EPS Transaction {self.merchant_transaction_id} - {self.amount} {self.currency} ({self.status})"
    
    def is_successful(self):
        """Check if transaction is successful"""
        return self.status == 'completed' and self.payment_status in ['success', 'completed']
    
    def can_be_refunded(self):
        """Check if transaction can be refunded"""
        return self.status == 'completed' and self.payment_status == 'success'


class EpsTokenCache(models.Model):
    """EPS Token Caching Model (Alternative to Redis)"""
    
    key = models.CharField(
        max_length=100,
        unique=True,
        help_text="Cache key (e.g., 'eps_token')"
    )
    value = models.TextField(
        help_text="Cached token value"
    )
    expires_at = models.DateTimeField(
        help_text="Token expiration time"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "EPS Token Cache"
        verbose_name_plural = "EPS Token Cache"
    
    def __str__(self):
        return f"Cache: {self.key}"
    
    def is_expired(self):
        """Check if token is expired"""
        from django.utils import timezone
        return timezone.now() > self.expires_at


class EpsWebhookLog(models.Model):
    """EPS Webhook/Callback Logging Model"""
    
    # Request Information
    method = models.CharField(max_length=10, default='POST')
    url = models.URLField(max_length=500)
    headers = models.JSONField(
        blank=True,
        null=True,
        help_text="Request headers"
    )
    body = models.TextField(
        blank=True,
        help_text="Request body/payload"
    )
    query_params = models.JSONField(
        blank=True,
        null=True,
        help_text="URL query parameters"
    )
    
    # Response Information
    response_status = models.IntegerField(
        blank=True,
        null=True,
        help_text="HTTP response status code"
    )
    response_body = models.TextField(
        blank=True,
        help_text="Response body"
    )
    
    # Processing Information
    is_processed = models.BooleanField(
        default=False,
        help_text="Whether webhook was processed successfully"
    )
    processing_errors = models.TextField(
        blank=True,
        help_text="Any errors during processing"
    )
    
    # Associated Transaction
    transaction = models.ForeignKey(
        EpsTransaction,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="Related EPS transaction"
    )
    
    # Client Information
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text="Client IP address"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="Client user agent"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "EPS Webhook Log"
        verbose_name_plural = "EPS Webhook Logs"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Webhook {self.method} {self.url} - {self.created_at}"
