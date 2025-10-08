from django.contrib import admin

from globalapp.models import SoftwareAsset
from solo.admin import SingletonModelAdmin
# Register your models here.
# admin.site.register(BaseBeneficariesModel)
admin.site.register(SoftwareAsset, SingletonModelAdmin)
# admin.site.register(EmailConfigure, SingletonModelAdmin)