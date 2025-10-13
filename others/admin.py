from django.contrib import admin, messages
from django.utils import timezone
from datetime import timedelta
from .models import Purchases
from others.models import BkashConfiguration, ExtraFeature, Package, PackageItem, Purchases, Tutorial, UddoktapayConfiguration,Additional
from solo.admin import SingletonModelAdmin
from django.db.models import Sum
import requests
import json
# Register your models here.
@admin.register(PackageItem)
class PackageItemAdmin(admin.ModelAdmin):
    list_display = ['field_name', 'color']

@admin.register(Package)
class PackageAdmin(SingletonModelAdmin):
    pass

@admin.register(Tutorial)
class TutorialAdmin(admin.ModelAdmin):
    list_display = ['title', 'video_url']

# Steadfast Courier API credentials
STEADFAST_API_KEY = "drkuephiwys6jmhq41ynz7kucokduzyj"
STEADFAST_SECRET_KEY = "xckh1t92ggvmfc21kgqhlvcu"
STEADFAST_BASE_URL = "https://portal.packzy.com/api/v1"

# Admin Action
def send_to_courier(modeladmin, request, queryset):
    orders_data = []

    for purchase in queryset:
        if not purchase.delivery_address or not getattr(purchase.user, 'phone_number', None):
            messages.warning(
                request,
                f"Purchase ID {purchase.id} skipped — Missing delivery address or phone number."
            )
            continue

        recipient_name = (
            purchase.user.get_full_name()
            if hasattr(purchase.user, 'get_full_name') and purchase.user.get_full_name()
            else purchase.user.email
        )

        # Make sure essential fields are present and valid
        if not all([
            purchase.id,
            recipient_name,
            purchase.delivery_address,
            purchase.user.phone_number,
            purchase.amount is not None
        ]):
            messages.warning(
                request,
                f"Purchase ID {purchase.id} skipped — Missing required fields."
            )
            continue

        orders_data.append({
            "invoice": str(purchase.id),
            "recipient_name": recipient_name,
            "recipient_address": purchase.delivery_address,
            "recipient_phone": purchase.user.phone_number,
            "cod_amount": float(purchase.amount),
            "note": purchase.note or "",
        })

    if not orders_data:
        messages.error(request, "No valid purchases found to send.")
        return

    try:
        # Debug print the payload
        print("Payload to send:", json.dumps(orders_data, indent=2))

        response = requests.post(
            f"{STEADFAST_BASE_URL}/create_order/",
            headers={
                "Api-Key": STEADFAST_API_KEY,
                "Secret-Key": STEADFAST_SECRET_KEY,
                "Content-Type": "application/json"
            },
            # Send orders list directly, not inside 'data'
            json=orders_data,
            timeout=15,
        )

        print("Response status:", response.status_code)
        print("Response text:", response.text)

        data = response.json()

        if isinstance(data, list):
            success_count = sum(1 for item in data if item.get("status") == "success")
            fail_count = len(data) - success_count
            messages.success(request, f"Courier request completed: {success_count} success, {fail_count} failed.")
        else:
            messages.error(request, f"Courier API error: {data}")

    except requests.exceptions.Timeout:
        messages.error(request, "Courier API request timed out.")
    except Exception as e:
        messages.error(request, f"Courier API request failed: {e}")

send_to_courier.short_description = "Send selected purchases to Courier"


# Custom filter for ExtraFeature price range
class ExtraFeaturePriceFilter(admin.SimpleListFilter):
    title = 'Extra Feature Price'
    parameter_name = 'extra_feature_price'

    def lookups(self, request, model_admin):
        return [
            ('low', 'Below 1000'),
            ('high', '1000 and above'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'low':
            return queryset.filter(extra_features__price__lt=1000).distinct()
        elif self.value() == 'high':
            return queryset.filter(extra_features__price__gte=1000).distinct()
        return queryset


@admin.register(Purchases)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user_email', 'payment_method', 'payment_status',
        'amount', 'trx_number', 'status', 'created_at_bdt',
    )
    list_filter = ('status', 'payment_status', 'extra_features')
    search_fields = ('user__email', 'trx_number', 'whatsapp_number', 'extra_features__name')
    ordering = ('-created_at',)
    change_list_template = 'admin/custom_admin/purchase_changelist.html'
    actions = [send_to_courier]  # <-- Added action here

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'

    def created_at_bdt(self, obj):
        """Display created_at in Bangladesh Time (BDT)"""
        from django.utils import timezone
        from datetime import datetime
        import pytz
        
        if obj.created_at:
            # Convert to Bangladesh timezone
            bdt_tz = pytz.timezone('Asia/Dhaka')
            bdt_time = obj.created_at.astimezone(bdt_tz)
            return bdt_time.strftime('%Y-%m-%d %I:%M:%S %p')  # 12-hour format with AM/PM
        return '-'
    created_at_bdt.short_description = 'Created At (BDT)'
    created_at_bdt.admin_order_field = 'created_at'  # Allow sorting by this field

    def changelist_view(self, request, extra_context=None):
        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        start_of_month = today.replace(day=1)

        this_month_amount = Purchases.objects.filter(
            created_at__date__gte=start_of_month,
            payment_status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0

        this_week_amount = Purchases.objects.filter(
            created_at__date__gte=start_of_week,
            payment_status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0

        today_amount = Purchases.objects.filter(
            created_at__date=today,
            payment_status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0

        pending_amount = Purchases.objects.filter(
            payment_status='pending'
        ).aggregate(total=Sum('amount'))['total'] or 0

        extra_context = extra_context or {}
        extra_context.update({
            'this_month_amount': f"{this_month_amount:,.2f}",
            'this_week_amount': f"{this_week_amount:,.2f}",
            'today_amount': f"{today_amount:,.2f}",
            'pending_amount': f"{pending_amount:,.2f}",
        })

        return super().changelist_view(request, extra_context=extra_context)
admin.site.register(ExtraFeature)
admin.site.register(Additional)
admin.site.register(BkashConfiguration,SingletonModelAdmin)
admin.site.register(UddoktapayConfiguration,SingletonModelAdmin)