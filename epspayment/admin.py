from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
import json

from .models import EpsConfiguration, EpsTransaction, EpsTokenCache, EpsWebhookLog


@admin.register(EpsConfiguration)
class EpsConfigurationAdmin(admin.ModelAdmin):
    list_display = ['merchant_id', 'store_id', 'is_active', 'is_sandbox', 'base_url', 'created_at']
    list_filter = ['is_active', 'is_sandbox', 'created_at']
    search_fields = ['merchant_id', 'store_id', 'username']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Configuration', {
            'fields': ('base_url', 'username', 'password', 'hash_key')
        }),
        ('Merchant Information', {
            'fields': ('merchant_id', 'store_id')
        }),
        ('Environment Settings', {
            'fields': ('is_active', 'is_sandbox')
        }),
        ('Callback URLs (Optional)', {
            'fields': ('success_url', 'fail_url', 'cancel_url'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def save_model(self, request, obj, form, change):
        # Ensure only one active configuration
        if obj.is_active:
            EpsConfiguration.objects.filter(is_active=True).exclude(pk=obj.pk).update(is_active=False)
        super().save_model(request, obj, form, change)


@admin.register(EpsTransaction)
class EpsTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'merchant_transaction_id', 
        'customer_name', 
        'amount', 
        'currency',
        'status_badge', 
        'payment_status_badge',
        'is_verified',
        'created_at'
    ]
    list_filter = [
        'status', 
        'payment_status', 
        'currency', 
        'is_verified',
        'created_at',
        'completed_at'
    ]
    search_fields = [
        'merchant_transaction_id', 
        'eps_transaction_id',
        'customer_order_id',
        'customer_name', 
        'customer_email',
        'customer_phone'
    ]
    readonly_fields = [
        'id',
        'merchant_transaction_id',
        'eps_transaction_id',
        'redirect_url',
        'callback_data_formatted',
        'is_verified',
        'verification_attempts',
        'last_verification_at',
        'ip_address',
        'user_agent',
        'created_at',
        'updated_at',
        'completed_at'
    ]
    
    fieldsets = (
        ('Transaction Information', {
            'fields': (
                'id',
                'merchant_transaction_id',
                'eps_transaction_id',
                'customer_order_id',
                'amount',
                'currency',
                'status',
                'payment_status'
            )
        }),
        ('Customer Information', {
            'fields': (
                'customer_name',
                'customer_email',
                'customer_phone',
                'customer_address',
                'customer_city',
                'customer_state',
                'customer_postcode',
                'customer_country'
            )
        }),
        ('Product Information', {
            'fields': (
                'product_name',
                'product_category',
                'no_of_items'
            )
        }),
        ('Payment Details', {
            'fields': (
                'redirect_url',
                'financial_entity_id',
                'financial_entity_name'
            )
        }),
        ('Verification', {
            'fields': (
                'is_verified',
                'verification_attempts',
                'last_verification_at'
            ),
            'classes': ('collapse',)
        }),
        ('Callback Data', {
            'fields': ('callback_data_formatted',),
            'classes': ('collapse',)
        }),
        ('Technical Information', {
            'fields': (
                'ip_address',
                'user_agent',
                'user'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
                'completed_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'processing': '#17a2b8',
            'completed': '#28a745',
            'failed': '#dc3545',
            'cancelled': '#6c757d',
            'refunded': '#007bff'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.status.upper()
        )
    status_badge.short_description = 'Status'
    
    def payment_status_badge(self, obj):
        if not obj.payment_status:
            return '-'
        
        colors = {
            'success': '#28a745',
            'completed': '#28a745',
            'failed': '#dc3545',
            'fail': '#dc3545',
            'cancelled': '#6c757d',
            'cancel': '#6c757d'
        }
        color = colors.get(obj.payment_status.lower(), '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.payment_status.upper()
        )
    payment_status_badge.short_description = 'Payment Status'
    
    def callback_data_formatted(self, obj):
        if obj.callback_data:
            return format_html('<pre>{}</pre>', json.dumps(obj.callback_data, indent=2))
        return 'No callback data'
    callback_data_formatted.short_description = 'Callback Data'
    
    actions = ['verify_transactions']
    
    def verify_transactions(self, request, queryset):
        from .utils import get_eps_token, generate_eps_hash, get_eps_configuration
        import requests
        
        verified_count = 0
        error_count = 0
        
        try:
            eps_config = get_eps_configuration()
            token = get_eps_token()
            
            for transaction in queryset:
                try:
                    x_hash = generate_eps_hash(transaction.merchant_transaction_id, eps_config.hash_key)
                    
                    response = requests.get(
                        f"{eps_config.base_url}/EPSEngine/CheckMerchantTransactionStatus",
                        params={'merchantTransactionId': transaction.merchant_transaction_id},
                        headers={
                            'x-hash': x_hash,
                            'Authorization': f'Bearer {token}',
                            'Content-Type': 'application/json',
                        },
                        timeout=30
                    )
                    
                    response.raise_for_status()
                    transaction_data = response.json()
                    
                    if not transaction_data.get('ErrorCode'):
                        transaction.payment_status = transaction_data.get('Status', '')
                        transaction.financial_entity_name = transaction_data.get('FinancialEntity', '')
                        transaction.is_verified = True
                        transaction.verification_attempts += 1
                        
                        eps_status = transaction_data.get('Status', '').lower()
                        if eps_status in ['success', 'completed']:
                            transaction.status = 'completed'
                        elif eps_status in ['failed', 'fail']:
                            transaction.status = 'failed'
                        elif eps_status in ['cancelled', 'cancel']:
                            transaction.status = 'cancelled'
                        
                        transaction.save()
                        verified_count += 1
                    else:
                        error_count += 1
                        
                except Exception:
                    error_count += 1
                    
        except Exception:
            self.message_user(request, "Failed to verify transactions. Please check EPS configuration.", level='error')
            return
        
        self.message_user(
            request,
            f"Verified {verified_count} transactions successfully. {error_count} errors occurred.",
            level='success' if error_count == 0 else 'warning'
        )
    
    verify_transactions.short_description = "Verify selected transactions with EPS"


@admin.register(EpsTokenCache)
class EpsTokenCacheAdmin(admin.ModelAdmin):
    list_display = ['key', 'expires_at', 'is_expired_display', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['key']
    readonly_fields = ['created_at', 'updated_at', 'is_expired_display']
    
    def is_expired_display(self, obj):
        is_expired = obj.is_expired()
        color = '#dc3545' if is_expired else '#28a745'
        text = 'EXPIRED' if is_expired else 'VALID'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            text
        )
    is_expired_display.short_description = 'Status'
    
    actions = ['clear_expired_tokens']
    
    def clear_expired_tokens(self, request, queryset):
        expired_tokens = queryset.filter(expires_at__lt=timezone.now())
        count = expired_tokens.count()
        expired_tokens.delete()
        self.message_user(request, f"Cleared {count} expired tokens.", level='success')
    
    clear_expired_tokens.short_description = "Clear expired tokens"


@admin.register(EpsWebhookLog)
class EpsWebhookLogAdmin(admin.ModelAdmin):
    list_display = [
        'method',
        'url_short',
        'response_status',
        'is_processed',
        'transaction_link',
        'created_at'
    ]
    list_filter = [
        'method',
        'response_status',
        'is_processed',
        'created_at'
    ]
    search_fields = ['url', 'body', 'ip_address']
    readonly_fields = [
        'method',
        'url',
        'headers_formatted',
        'body_formatted',
        'query_params_formatted',
        'response_status',
        'response_body',
        'ip_address',
        'user_agent',
        'created_at'
    ]
    
    fieldsets = (
        ('Request Information', {
            'fields': (
                'method',
                'url',
                'headers_formatted',
                'body_formatted',
                'query_params_formatted'
            )
        }),
        ('Response Information', {
            'fields': (
                'response_status',
                'response_body'
            )
        }),
        ('Processing Information', {
            'fields': (
                'is_processed',
                'processing_errors',
                'transaction'
            )
        }),
        ('Client Information', {
            'fields': (
                'ip_address',
                'user_agent'
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    def url_short(self, obj):
        return obj.url[:50] + '...' if len(obj.url) > 50 else obj.url
    url_short.short_description = 'URL'
    
    def transaction_link(self, obj):
        if obj.transaction:
            url = reverse('admin:epspayment_epstransaction_change', args=[obj.transaction.id])
            return format_html('<a href="{}">{}</a>', url, obj.transaction.merchant_transaction_id)
        return '-'
    transaction_link.short_description = 'Transaction'
    
    def headers_formatted(self, obj):
        if obj.headers:
            return format_html('<pre>{}</pre>', json.dumps(obj.headers, indent=2))
        return 'No headers'
    headers_formatted.short_description = 'Headers'
    
    def body_formatted(self, obj):
        if obj.body:
            try:
                parsed = json.loads(obj.body)
                return format_html('<pre>{}</pre>', json.dumps(parsed, indent=2))
            except:
                return format_html('<pre>{}</pre>', obj.body)
        return 'No body'
    body_formatted.short_description = 'Body'
    
    def query_params_formatted(self, obj):
        if obj.query_params:
            return format_html('<pre>{}</pre>', json.dumps(obj.query_params, indent=2))
        return 'No query parameters'
    query_params_formatted.short_description = 'Query Parameters'


# Custom admin site configuration
admin.site.site_header = "EPS Payment Administration"
admin.site.site_title = "EPS Payment Admin"
admin.site.index_title = "Welcome to EPS Payment Administration"
