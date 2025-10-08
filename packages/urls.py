"""
Package URLs
"""
from django.urls import path
from . import views

app_name = 'packages'

urlpatterns = [
    # Package listing and details
    path('api/packages/', views.get_available_packages, name='available_packages'),
    path('api/packages/<int:package_id>/', views.get_package_details, name='package_details'),
    
    # Package purchase
    path('api/packages/purchase/', views.purchase_package, name='purchase_package'),
    
    # User package management
    path('api/user/packages/', views.get_user_packages, name='user_packages'),
    path('api/user/packages/usage/', views.get_package_usage, name='package_usage'),
]