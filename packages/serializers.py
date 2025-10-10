"""
Package Serializers
"""
from rest_framework import serializers
from .models import Package, UserPackage, PackageFeatureUsage, DailyOrderUsage
from django.contrib.auth.models import User


class PackageSerializer(serializers.ModelSerializer):
    """Serializer for Package model"""
    features_list = serializers.ReadOnlyField(source='get_features_list')
    
    class Meta:
        model = Package
        fields = [
            'id', 'name', 'package_type', 'duration_type', 'price', 'duration_days',
            'description', 'max_listings', 'max_images_per_listing', 'featured_listings',
            'daily_order_limit', 'priority_support', 'analytics_access', 'bulk_upload', 'api_access',
            'is_active', 'is_popular', 'features_list', 'created_at'
        ]


class UserPackageSerializer(serializers.ModelSerializer):
    """Serializer for UserPackage model"""
    package = PackageSerializer(read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    remaining_days = serializers.ReadOnlyField(source='get_remaining_days')
    is_currently_active = serializers.ReadOnlyField(source='is_active')
    
    class Meta:
        model = UserPackage
        fields = [
            'id', 'user', 'user_email', 'user_username', 'package', 'status',
            'purchase_date', 'start_date', 'end_date', 'amount_paid', 
            'payment_method', 'transaction_id', 'auto_renewal',
            'remaining_days', 'is_currently_active', 'created_at'
        ]
        read_only_fields = ['user', 'purchase_date', 'created_at']


class PackageFeatureUsageSerializer(serializers.ModelSerializer):
    """Serializer for PackageFeatureUsage model"""
    can_create_listing = serializers.ReadOnlyField()
    can_create_featured_listing = serializers.ReadOnlyField()
    
    class Meta:
        model = PackageFeatureUsage
        fields = [
            'id', 'listings_used', 'featured_listings_used',
            'can_create_listing', 'can_create_featured_listing',
            'created_at', 'updated_at'
        ]


class PackagePurchaseSerializer(serializers.Serializer):
    """Serializer for package purchase request"""
    package_id = serializers.IntegerField()
    payment_method = serializers.CharField(default='eps')
    
    def validate_package_id(self, value):
        """Validate that package exists and is active"""
        try:
            package = Package.objects.get(id=value, is_active=True)
            return value
        except Package.DoesNotExist:
            raise serializers.ValidationError("Package not found or inactive")


class UserProfilePackageSerializer(serializers.Serializer):
    """Serializer for user profile package information"""
    current_package = UserPackageSerializer(read_only=True)
    package_history = UserPackageSerializer(many=True, read_only=True)
    feature_usage = PackageFeatureUsageSerializer(read_only=True)
    available_packages = PackageSerializer(many=True, read_only=True)


class DailyOrderUsageSerializer(serializers.ModelSerializer):
    """Serializer for DailyOrderUsage model"""
    can_order_today = serializers.ReadOnlyField()
    remaining_orders_today = serializers.ReadOnlyField(source='get_remaining_orders_today')
    daily_limit = serializers.IntegerField(source='user_package.package.daily_order_limit', read_only=True)
    is_unlimited = serializers.SerializerMethodField()
    
    class Meta:
        model = DailyOrderUsage
        fields = [
            'id', 'date', 'orders_used', 'daily_limit', 
            'can_order_today', 'remaining_orders_today', 'is_unlimited',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['date', 'created_at', 'updated_at']
    
    def get_is_unlimited(self, obj):
        return obj.user_package.package.daily_order_limit == 0


class DailyOrderStatusSerializer(serializers.Serializer):
    """Serializer for daily order status response"""
    can_order = serializers.BooleanField()
    remaining_orders = serializers.IntegerField()
    daily_limit = serializers.IntegerField()
    orders_used_today = serializers.IntegerField()
    is_unlimited = serializers.BooleanField()
    package_name = serializers.CharField()
    package_type = serializers.CharField()