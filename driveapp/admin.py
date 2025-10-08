from django.contrib import admin

from driveapp.models import District, District2, Division, Division2, Mouzamapdata, SubDistrict

# Register your models here.
class MouzamapdataAdmin(admin.ModelAdmin):
    search_fields = ['district_name']  # Replace with actual field names you want to search by
class SubDistrictAdmin(admin.ModelAdmin):
    search_fields = ['name']  # Replace with actual field names you want to search by
admin.site.register(Mouzamapdata, MouzamapdataAdmin)
admin.site.register(Division)
admin.site.register(District)
admin.site.register(District2)
admin.site.register(Division2)
admin.site.register(SubDistrict,SubDistrictAdmin)