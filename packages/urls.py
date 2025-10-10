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
    path('api/user/packages/cleanup/', views.cleanup_pending_packages, name='cleanup_pending_packages'),
    
    # Daily order limit endpoints
    path('api/user/packages/daily-status/', views.get_daily_order_status, name='daily_order_status'),
    path('api/user/packages/validate-order/', views.validate_order_limit, name='validate_order_limit'),
    path('api/user/packages/usage-history/', views.get_daily_usage_history, name='daily_usage_history'),
    
    # Free order processing
    path('api/user/packages/process-free-order/', views.process_free_order, name='process_free_order'),
]