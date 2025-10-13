"""
Package Management Models
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from django.core.validators import MinValueValidator

User = get_user_model()


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
    
    # Status
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    
    # Metadata
    description = models.TextField(blank=True)
    
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
        """Calculate total price based on file count"""
        if file_count <= 0:
            return Decimal('0.00')
        return self.base_price * file_count


class Package(models.Model):
    """
    Package model for ProSeller and Regular packages
    """
    PACKAGE_TYPES = [
        ('regular', 'Regular'),
        ('proseller', 'ProSeller'),
    ]
    
    DURATION_TYPES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('lifetime', 'Lifetime'),
    ]
    
    name = models.CharField(max_length=100)
    package_type = models.CharField(max_length=20, choices=PACKAGE_TYPES)
    duration_type = models.CharField(max_length=20, choices=DURATION_TYPES, default='monthly')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.IntegerField(help_text="Duration in days (0 for lifetime)")
    
    # Package Features
    description = models.TextField(blank=True)
    max_listings = models.IntegerField(default=0, help_text="0 means unlimited")
    max_images_per_listing = models.IntegerField(default=5)
    featured_listings = models.IntegerField(default=0, help_text="Number of featured listings allowed")
    
    # Daily Limits
    daily_order_limit = models.IntegerField(default=0, help_text="Daily order limit (0 means unlimited)")
    
    # Advanced Features
    priority_support = models.BooleanField(default=False)
    analytics_access = models.BooleanField(default=False)
    bulk_upload = models.BooleanField(default=False)
    api_access = models.BooleanField(default=False)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False, help_text="Mark as popular package")
    sort_order = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sort_order', 'price']
        verbose_name = 'Package'
        verbose_name_plural = 'Packages'
    
    def __str__(self):
        return f"{self.name} - {self.get_package_type_display()} ({self.get_duration_type_display()})"
    
    def get_features_list(self):
        """Get list of package features"""
        features = []
        
        if self.max_listings == 0:
            features.append("Unlimited listings")
        else:
            features.append(f"Up to {self.max_listings} listings")
        
        features.append(f"Up to {self.max_images_per_listing} images per listing")
        
        if self.featured_listings > 0:
            features.append(f"{self.featured_listings} featured listings")
        
        # Daily Order Limit
        if self.daily_order_limit == 0:
            features.append("Unlimited daily orders")
        else:
            features.append(f"{self.daily_order_limit} orders per day")
        
        # Advanced Features
        if self.priority_support:
            features.append("Priority customer support")
        
        if self.analytics_access:
            features.append("Advanced analytics")
        
        if self.bulk_upload:
            features.append("Bulk upload")
        
        if self.api_access:
            features.append("API access")
        
        return features


class UserPackage(models.Model):
    """
    Track user package purchases and subscriptions
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Payment Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='packages')
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    
    # Purchase Information
    purchase_date = models.DateTimeField(auto_now_add=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Payment Information
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, default='eps')
    transaction_id = models.CharField(max_length=255, unique=True)
    payment_gateway_response = models.JSONField(blank=True, null=True)
    
    # Auto-renewal (for future implementation)
    auto_renewal = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User Package'
        verbose_name_plural = 'User Packages'
    
    def __str__(self):
        return f"{self.user.username} - {self.package.name} ({self.status})"
    
    def is_active(self):
        """Check if package is currently active"""
        if self.status != 'active':
            return False
        
        if self.end_date and timezone.now() > self.end_date:
            # Auto-expire if end date has passed
            self.status = 'expired'
            self.save()
            return False
        
        return True
    
    def activate_package(self):
        """Activate the package after successful payment"""
        self.status = 'active'
        self.start_date = timezone.now()
        
        # Set end date based on package duration
        if self.package.duration_days > 0:
            from datetime import timedelta
            self.end_date = self.start_date + timedelta(days=self.package.duration_days)
        else:
            # Lifetime package
            self.end_date = None
        
        self.save()
    
    def get_remaining_days(self):
        """Get remaining days for the package"""
        if not self.end_date:
            return None  # Lifetime package
        
        if not self.is_active():
            return 0
        
        remaining = self.end_date - timezone.now()
        return max(0, remaining.days)
    
    def can_order_today(self, file_count=1):
        """Check if user can make orders today based on daily limit with specified file count"""
        if not self.is_active():
            return False
        
        today_usage = DailyOrderUsage.get_or_create_today_usage(self)
        return today_usage.can_order_today(file_count=file_count)
    
    def get_daily_order_status(self):
        """Get daily order status information"""
        if not self.is_active():
            return {
                'can_order': False,
                'remaining_orders': 0,
                'daily_limit': 0,
                'orders_used_today': 0,
                'is_unlimited': False
            }
        
        today_usage = DailyOrderUsage.get_or_create_today_usage(self)
        daily_limit = self.package.daily_order_limit
        
        return {
            'can_order': today_usage.can_order_today(),
            'remaining_orders': today_usage.get_remaining_orders_today(),
            'daily_limit': daily_limit,
            'orders_used_today': today_usage.orders_used,
            'is_unlimited': daily_limit == 0
        }
    
    def increment_daily_order_usage(self, file_count=1):
        """Increment today's order usage by specified file count"""
        if not self.is_active():
            return False
        
        today_usage = DailyOrderUsage.get_or_create_today_usage(self)
        
        if today_usage.can_order_today(file_count=file_count):
            today_usage.increment_order_usage(file_count=file_count)
            return True
        return False


class PackageFeatureUsage(models.Model):
    """
    Track feature usage for user packages
    """
    user_package = models.OneToOneField(UserPackage, on_delete=models.CASCADE, related_name='usage')
    
    # Usage counters
    listings_used = models.IntegerField(default=0)
    featured_listings_used = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Package Feature Usage'
        verbose_name_plural = 'Package Feature Usage'
    
    def __str__(self):
        return f"{self.user_package.user.username} - {self.user_package.package.name} Usage"
    
    def can_create_listing(self):
        """Check if user can create more listings"""
        max_listings = self.user_package.package.max_listings
        if max_listings == 0:  # Unlimited
            return True
        return self.listings_used < max_listings
    
    def can_create_featured_listing(self):
        """Check if user can create featured listings"""
        return self.featured_listings_used < self.user_package.package.featured_listings
    
    def increment_listing_usage(self):
        """Increment listing usage counter"""
        self.listings_used += 1
        self.save()
    
    def increment_featured_listing_usage(self):
        """Increment featured listing usage counter"""
        self.featured_listings_used += 1
        self.save()


class DailyOrderUsage(models.Model):
    """
    Track daily order usage for user packages
    """
    user_package = models.ForeignKey(UserPackage, on_delete=models.CASCADE, related_name='daily_usage')
    date = models.DateField(default=timezone.now)
    orders_used = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user_package', 'date']
        verbose_name = 'Daily Order Usage'
        verbose_name_plural = 'Daily Order Usage'
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.user_package.user.username} - {self.date} - {self.orders_used} orders"
    
    def can_order_today(self, file_count=1):
        """Check if user can make more orders today with specified file count"""
        daily_limit = self.user_package.package.daily_order_limit
        if daily_limit == 0:  # Unlimited
            return True
        return (self.orders_used + file_count) <= daily_limit
    
    def get_remaining_orders_today(self):
        """Get remaining orders for today"""
        daily_limit = self.user_package.package.daily_order_limit
        if daily_limit == 0:  # Unlimited
            return -1  # Indicates unlimited
        return max(0, daily_limit - self.orders_used)
    
    def increment_order_usage(self, file_count=1):
        """Increment daily order usage by specified file count"""
        self.orders_used += file_count
        self.save()
        return self.orders_used
    
    @classmethod
    def get_or_create_today_usage(cls, user_package):
        """Get or create today's usage record for a user package"""
        today = timezone.now().date()
        usage, created = cls.objects.get_or_create(
            user_package=user_package,
            date=today,
            defaults={'orders_used': 0}
        )
        return usage
