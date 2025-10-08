"""
Package Admin Configuration
"""
from django.contrib import admin
from .models import Package, UserPackage, PackageFeatureUsage


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ['name', 'package_type', 'duration_type', 'price', 'duration_days', 'is_active', 'is_popular', 'created_at']
    list_filter = ['package_type', 'duration_type', 'is_active', 'is_popular']
    search_fields = ['name', 'description']
    ordering = ['sort_order', 'price']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'package_type', 'duration_type', 'price', 'duration_days', 'description')
        }),
        ('Features', {
            'fields': ('max_listings', 'max_images_per_listing', 'featured_listings', 'priority_support', 
                      'analytics_access', 'bulk_upload', 'api_access')
        }),
        ('Status & Display', {
            'fields': ('is_active', 'is_popular', 'sort_order')
        }),
    )


@admin.register(UserPackage)
class UserPackageAdmin(admin.ModelAdmin):
    list_display = ['user', 'package', 'status', 'start_date', 'end_date', 'amount_paid', 'payment_method', 'created_at']
    list_filter = ['status', 'payment_method', 'package__package_type', 'created_at']
    search_fields = ['user__username', 'user__email', 'transaction_id']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    readonly_fields = ['purchase_date', 'created_at', 'updated_at']
    
    fieldsets = (
        ('User & Package', {
            'fields': ('user', 'package', 'status')
        }),
        ('Dates', {
            'fields': ('purchase_date', 'start_date', 'end_date')
        }),
        ('Payment Information', {
            'fields': ('amount_paid', 'payment_method', 'transaction_id', 'payment_gateway_response')
        }),
        ('Settings', {
            'fields': ('auto_renewal',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'package')


@admin.register(PackageFeatureUsage)
class PackageFeatureUsageAdmin(admin.ModelAdmin):
    list_display = ['user_package', 'listings_used', 'featured_listings_used', 'updated_at']
    list_filter = ['user_package__package__package_type']
    search_fields = ['user_package__user__username']
    ordering = ['-updated_at']
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user_package__user', 'user_package__package')
