"""
Package Management Models
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

User = get_user_model()


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
