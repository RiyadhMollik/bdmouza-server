"""
Package Serializers
"""
from rest_framework import serializers
from .models import Package, UserPackage, PackageFeatureUsage
from django.contrib.auth.models import User


class PackageSerializer(serializers.ModelSerializer):
    """Serializer for Package model"""
    features_list = serializers.ReadOnlyField(source='get_features_list')
    
    class Meta:
        model = Package
        fields = [
            'id', 'name', 'package_type', 'duration_type', 'price', 'duration_days',
            'description', 'max_listings', 'max_images_per_listing', 'featured_listings',
            'priority_support', 'analytics_access', 'bulk_upload', 'api_access',
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