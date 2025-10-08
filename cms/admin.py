from django.contrib import admin

from cms.models import FAQ, Banner, BannerItem, BannerLMS, Blog, Button, Counter, CounterItem, Facilities, FacilitiesItem, Page, SpecialCta, Testimonial
from solo.admin import SingletonModelAdmin
# Register your models here.
admin.site.register(Page)
admin.site.register(FAQ)
admin.site.register(Testimonial)
admin.site.register(Blog)
admin.site.register(Banner)
admin.site.register(BannerItem)
admin.site.register(Button)
admin.site.register(CounterItem)
admin.site.register(BannerLMS)
@admin.register(Counter)
class CounterAdmin(SingletonModelAdmin):
    pass

admin.site.register(FacilitiesItem)
@admin.register(Facilities)
class FacilitiesAdmin(SingletonModelAdmin):
    pass

@admin.register(SpecialCta)
class SpecialCtaAdmin(SingletonModelAdmin):
    pass