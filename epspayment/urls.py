"""
EPS Payment URL Configuration
"""
from django.urls import path, include
from . import views

app_name = 'epspayment'

urlpatterns = [
    # Payment initialization
    path('eps/initialize/', views.initialize_eps_payment, name='initialize_payment'),
    
    # Test validation endpoint
    path('eps/test-validation/', views.test_eps_validation, name='test_validation'),
    
    # Transaction verification
    path('eps/verify/<str:merchant_transaction_id>/', views.verify_eps_transaction, name='verify_transaction'),
    
    # Payment callback (from EPS)
    path('eps/callback/', views.eps_payment_callback, name='payment_callback'),
    
    # Transaction status
    path('eps/status/<str:merchant_transaction_id>/', views.get_transaction_status, name='transaction_status'),
    
    # Configuration
    path('eps/config/', views.get_eps_configuration_api, name='configuration'),
]