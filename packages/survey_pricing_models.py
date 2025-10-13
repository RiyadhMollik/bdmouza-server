"""
Survey Type Pricing Models
"""
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class SurveyTypePricing(models.Model):
    """
    Pricing model for different survey types (SA_RS, CS, BS, etc.)
    """
    SURVEY_TYPES = [
        ('SA_RS', 'SA/RS Survey'),
        ('CS', 'CS Survey'),
        ('BS', 'BS Survey'),
        ('SA', 'SA Survey'),
        ('RS', 'RS Survey'),
    ]
    
    survey_type = models.CharField(
        max_length=20, 
        choices=SURVEY_TYPES, 
        unique=True,
        help_text="Survey type identifier"
    )
    
    display_name = models.CharField(
        max_length=100,
        help_text="Display name in Bengali/English"
    )
    
    # Pricing structure
    base_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Base price per file"
    )
    
    # Bulk pricing tiers (optional)
    bulk_discount_enabled = models.BooleanField(default=False)
    bulk_tier_1_count = models.IntegerField(
        default=10,
        help_text="Files needed for tier 1 discount"
    )
    bulk_tier_1_discount = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Discount percentage for tier 1"
    )
    
    bulk_tier_2_count = models.IntegerField(
        default=50,
        help_text="Files needed for tier 2 discount"
    )
    bulk_tier_2_discount = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Discount percentage for tier 2"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    
    # Metadata
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True, help_text="Internal notes")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sort_order', 'survey_type']
        verbose_name = 'Survey Type Pricing'
        verbose_name_plural = 'Survey Type Pricing'
    
    def __str__(self):
        return f"{self.survey_type} - ৳{self.base_price}"
    
    def calculate_price(self, file_count):
        """
        Calculate total price based on file count and bulk discounts
        """
        if file_count <= 0:
            return Decimal('0.00')
        
        base_total = self.base_price * file_count
        
        if not self.bulk_discount_enabled:
            return base_total
        
        # Apply bulk discount
        discount = Decimal('0.00')
        
        if file_count >= self.bulk_tier_2_count:
            discount = self.bulk_tier_2_discount
        elif file_count >= self.bulk_tier_1_count:
            discount = self.bulk_tier_1_discount
        
        if discount > 0:
            discount_amount = base_total * (discount / Decimal('100'))
            return base_total - discount_amount
        
        return base_total
    
    def get_discount_info(self, file_count):
        """
        Get discount information for given file count
        """
        if not self.bulk_discount_enabled or file_count < self.bulk_tier_1_count:
            return {
                'has_discount': False,
                'discount_percentage': 0,
                'original_price': self.calculate_price(file_count),
                'final_price': self.calculate_price(file_count),
                'saved_amount': Decimal('0.00')
            }
        
        original_price = self.base_price * file_count
        final_price = self.calculate_price(file_count)
        
        if file_count >= self.bulk_tier_2_count:
            discount_percentage = self.bulk_tier_2_discount
        else:
            discount_percentage = self.bulk_tier_1_discount
        
        return {
            'has_discount': True,
            'discount_percentage': float(discount_percentage),
            'original_price': float(original_price),
            'final_price': float(final_price),
            'saved_amount': float(original_price - final_price)
        }


class FileOrder(models.Model):
    """
    Enhanced file order model with survey type pricing
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed'),
    ]
    
    # User and Order Info
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='file_orders')
    order_id = models.CharField(max_length=50, unique=True)
    
    # Survey Type
    survey_type = models.ForeignKey(
        SurveyTypePricing, 
        on_delete=models.PROTECT,
        related_name='orders'
    )
    
    # File Information
    file_count = models.IntegerField(validators=[MinValueValidator(1)])
    file_ids = models.JSONField(help_text="List of Google Drive file IDs")
    file_details = models.JSONField(help_text="Detailed file information", null=True, blank=True)
    
    # Pricing
    base_price_per_file = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    original_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    final_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Location Information
    division = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    upazila = models.CharField(max_length=100, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, default='pending')
    
    # Package Info (if using package-based order)
    is_package_order = models.BooleanField(default=False)
    package_info = models.JSONField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'File Order'
        verbose_name_plural = 'File Orders'
    
    def __str__(self):
        return f"Order {self.order_id} - {self.user.username} - {self.survey_type.survey_type}"
    
    def save(self, *args, **kwargs):
        if not self.order_id:
            # Generate unique order ID
            import uuid
            from django.utils import timezone
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.order_id = f"ORD{timestamp}{str(uuid.uuid4())[:8].upper()}"
        
        super().save(*args, **kwargs)
