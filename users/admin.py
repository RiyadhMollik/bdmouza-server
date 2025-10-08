from django.contrib import admin

from users.models import Users, Roles

# Register your models here.
@admin.register(Users)
class UsersAdmin(admin.ModelAdmin):
    search_fields = ['email'] 
admin.site.register(Roles)