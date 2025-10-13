"""
Package Admin Configuration
"""
from django.contrib import admin
from .models import Package, UserPackage, PackageFeatureUsage, DailyOrderUsage, SurveyTypePricing


@admin.register(SurveyTypePricing)
class SurveyTypePricingAdmin(admin.ModelAdmin):
    list_display = ['survey_type', 'display_name', 'base_price', 'is_active', 'sort_order', 'updated_at']
    list_filter = ['is_active', 'survey_type']
    search_fields = ['survey_type', 'display_name', 'description']
    ordering = ['sort_order', 'survey_type']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('survey_type', 'display_name', 'description')
        }),
        ('Pricing', {
            'fields': ('base_price',)
        }),
        ('Status & Display', {
            'fields': ('is_active', 'sort_order')
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']


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
            'fields': ('max_listings', 'max_images_per_listing', 'featured_listings', 'daily_order_limit', 
                      'priority_support', 'analytics_access', 'bulk_upload', 'api_access')
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


@admin.register(DailyOrderUsage)
class DailyOrderUsageAdmin(admin.ModelAdmin):
    list_display = ['user_package', 'date', 'orders_used', 'daily_limit_display', 'can_order_display']
    list_filter = ['date', 'user_package__package__package_type']
    search_fields = ['user_package__user__username', 'user_package__user__email']
    date_hierarchy = 'date'
    ordering = ['-date', '-orders_used']
    
    readonly_fields = ['created_at', 'updated_at']
    
    def daily_limit_display(self, obj):
        limit = obj.user_package.package.daily_order_limit
        return "Unlimited" if limit == 0 else f"{limit} orders"
    daily_limit_display.short_description = 'Daily Limit'
    
    def can_order_display(self, obj):
        return "✅" if obj.can_order_today() else "❌"
    can_order_display.short_description = 'Can Order'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user_package__user', 'user_package__package')
