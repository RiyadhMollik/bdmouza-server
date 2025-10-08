from django.db import models
from colorfield.fields import ColorField
from globalapp.models import Common
from solo.models import SingletonModel
from ckeditor.fields import RichTextField
from django.core.validators import RegexValidator
from decimal import Decimal
from users.models import Users
from .driver_utils import find_folder_by_name, share_drive_file
# Create your models here.
class PackageItem(Common):

    field_name = models.CharField(max_length=100)
    icon = models.FileField(upload_to='package_icons/')
    color = ColorField(default='#FF0000')  # Or use CharField if not using django-colorfield
    price_per_file = models.DecimalField(max_digits=10, decimal_places=2)
    file_limit = models.PositiveIntegerField(help_text="Maximum number of files allowed")
    is_static = models.BooleanField(default=False, null=True, blank=True)

    PACKAGE_TYPE_CHOICES = [
        ('bangladesh', 'Bangladesh'),
        ('division', 'Division'),
        ('district', 'District'),
        ('subdistrict', 'Subdistrict'),
        ('survey', 'Survey Type'),
    ]
    package_type = models.CharField(
        max_length=20,
        choices=PACKAGE_TYPE_CHOICES,
        null=True,
        blank=True,
        help_text="Type of package item"
    )

    file_range = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Range of files this package item covers (e.g. 1-50, All, etc.)"
    )


    def __str__(self):
        return f"{self.field_name} - ${self.price_per_file}"
    
class Package(SingletonModel):
    text = RichTextField()
    video_url = models.URLField(help_text="YouTube video URL")
    pro = models.ManyToManyField(PackageItem, related_name='packages_pro')
    regular = models.ManyToManyField(PackageItem, related_name='packages_regular')

    def __str__(self):
        return "Package Singleton"
    
class Tutorial(Common):
    title = models.CharField(max_length=255)
    descriptions = RichTextField()
    video_url = models.URLField(help_text="Enter a valid YouTube video URL")

    def __str__(self):
        return self.title
class BkashConfiguration(SingletonModel):
    name = models.CharField(max_length=100, default="bKash Config")
    sandbox = models.BooleanField(default=True, help_text="Enable sandbox mode for testing")

    app_key = models.CharField(max_length=255)
    app_secret = models.CharField(max_length=255)
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "bKash Configuration"

    def __str__(self):
        return f"{'Sandbox' if self.sandbox else 'Live'} bKash Config"
class Additional(Common):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return self.name

class ExtraFeature(Common):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    additionals = models.ManyToManyField(Additional, related_name='extra_features', blank=True)

    def __str__(self):
        return self.name  
class Purchases(Common):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('delivered', 'Delivered'),
    ]
    PAYMENT_METHODS = (
            ("bkash", "bKash"),
            ('eps', 'EPS'),
            ('others', 'Others'),
        )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default="bkash")
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='purchases')
    package = models.ForeignKey(PackageItem, on_delete=models.SET_NULL, null=True, blank=True)
    extra_features = models.ManyToManyField(ExtraFeature, blank=True,null=True, related_name='purchases')
    whatsapp_number = models.CharField(
        max_length=17,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Enter a valid WhatsApp number in the format: '+999999999'"
            )
        ],
        null=True,
        blank=True
    )
    mobile_number = models.CharField(
        max_length=17,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Enter a valid WhatsApp number in the format: '+999999999'"
            )
        ],
        null=True,
        blank=True
    )
    file_name = models.JSONField(default=list, blank=True)  # Django 3.1+ built-in JSONField
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='pending')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    trx_number = models.CharField(max_length=100, help_text="Transaction or reference number", null=True, blank=True)
    # New fields
    note = models.TextField(null=True, blank=True)
    delivery_address = models.TextField(null=True, blank=True)
    

    def __str__(self):
        return f"Purchase by {self.user.email} - {self.payment_status}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Save first, to get a valid ID

        # Process file sharing
        if isinstance(self.file_name, list):
            for name in self.file_name:
                # Check if it's a folder-style name (no .jpg or .pdf)
                if not name.lower().endswith(('.jpg', '.jpeg', '.pdf')):
                    # Extract the folder name (last part after "_")
                    folder_name = name.split("_")[-1].strip()
                    folder = find_folder_by_name(folder_name)
                    if folder:
                        try:
                            share_drive_file(folder["id"], self.user.email)
                        except Exception as e:
                            print(f"[ERROR] Failed to share folder '{folder_name}' with {self.user.email}: {e}")
        
class UddoktapayConfiguration(SingletonModel):
    sandbox = models.BooleanField(default=True)
    api_key = models.CharField(max_length=255)
    