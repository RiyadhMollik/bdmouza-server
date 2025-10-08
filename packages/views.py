"""
Package API Views
"""
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
import logging

from .models import Package, UserPackage, PackageFeatureUsage
from .serializers import (
    PackageSerializer, 
    UserPackageSerializer, 
    PackagePurchaseSerializer,
    UserProfilePackageSerializer,
    PackageFeatureUsageSerializer
)

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_available_packages(request):
    """
    Get all available packages for purchase
    """
    try:
        packages = Package.objects.filter(is_active=True).order_by('sort_order', 'price')
        serializer = PackageSerializer(packages, many=True)
        
        return Response({
            'success': True,
            'packages': serializer.data,
            'count': packages.count()
        })
    except Exception as e:
        logger.error(f"Error fetching packages: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error fetching packages'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_package_details(request, package_id):
    """
    Get detailed information about a specific package
    """
    try:
        package = get_object_or_404(Package, id=package_id, is_active=True)
        serializer = PackageSerializer(package)
        
        return Response({
            'success': True,
            'package': serializer.data
        })
    except Package.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Package not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching package details: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error fetching package details'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def purchase_package(request):
    """
    Purchase a package using EPS payment
    """
    print("Purchase package request data:", request.data)  # Debugging line
    try:
        serializer = PackagePurchaseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Invalid request data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        package_id = serializer.validated_data['package_id']
        payment_method = serializer.validated_data['payment_method']
        
        # Get the package
        package = get_object_or_404(Package, id=package_id, is_active=True)
        
        # Check if user already has an active package of the same type
        existing_active = UserPackage.objects.filter(
            user=request.user,
            package__package_type=package.package_type,
            status='active'
        ).first()
        
        if existing_active and existing_active.is_active():
            return Response({
                'success': False,
                'message': f'You already have an active {package.get_package_type_display()} package'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create UserPackage record with pending status
        with transaction.atomic():
            user_package = UserPackage.objects.create(
                user=request.user,
                package=package,
                amount_paid=package.price,
                payment_method=payment_method,
                transaction_id='',  # Will be updated with actual transaction ID
                status='pending'
            )
            
            # Generate unique transaction ID for payment
            from epspayment.utils import generate_merchant_transaction_id
            merchant_transaction_id = generate_merchant_transaction_id()
            user_package.transaction_id = merchant_transaction_id
            user_package.save()
            
            # Prepare payment data for EPS
            payment_data = {
                'amount': float(package.price),
                'customer_name': getattr(request.user, 'name', '') or getattr(request.user, 'username', '') or 'Customer',
                'customer_email': request.user.email or 'customer@example.com',
                'customer_phone': getattr(request.user, 'phone_number', '01700000000') or '01700000000',
                'order_id': f"PKG-{user_package.id}",
                'description': f"{package.name} Package Purchase",
                'user_id': request.user.id,
                'package_id': package.id,
                'user_package_id': user_package.id,
                'purchase_type': 'package'
            }
            
            # Initialize EPS payment
            from epspayment.utils import create_eps_payment
            print("Payment data:", payment_data)  # Debug payment data
            eps_result = create_eps_payment(payment_data)
            print("EPS result:", eps_result)  # Debug EPS response
            
            if eps_result.get('success'):
                # Update user_package with EPS transaction ID
                user_package.transaction_id = eps_result.get('transaction_id')
                user_package.save()
                
                logger.info(f"Package purchase initiated: User {request.user.id}, Package {package.id}")
                
                return Response({
                    'success': True,
                    'message': 'Package purchase initiated',
                    'payment_url': eps_result.get('payment_url'),
                    'transaction_id': eps_result.get('transaction_id'),
                    'user_package_id': user_package.id,
                    'package': PackageSerializer(package).data
                })
            else:
                # Delete the user_package if payment initiation failed
                user_package.delete()
                return Response({
                    'success': False,
                    'message': eps_result.get('message', 'Failed to initiate payment')
                }, status=status.HTTP_400_BAD_REQUEST)
                
    except Exception as e:
        logger.error(f"Error purchasing package: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error processing package purchase'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_packages(request):
    """
    Get user's package information including current package and history
    """
    try:
        # Get current active package
        current_package = UserPackage.objects.filter(
            user=request.user,
            status='active'
        ).select_related('package').first()
        
        if current_package and not current_package.is_active():
            current_package = None
        
        # Get package history
        package_history = UserPackage.objects.filter(
            user=request.user
        ).select_related('package').order_by('-created_at')
        
        # Get feature usage for current package
        feature_usage = None
        if current_package:
            feature_usage, created = PackageFeatureUsage.objects.get_or_create(
                user_package=current_package
            )
        
        # Get available packages for upgrade
        available_packages = Package.objects.filter(is_active=True).order_by('sort_order', 'price')
        
        return Response({
            'success': True,
            'current_package': UserPackageSerializer(current_package).data if current_package else None,
            'package_history': UserPackageSerializer(package_history, many=True).data,
            'feature_usage': PackageFeatureUsageSerializer(feature_usage).data if feature_usage else None,
            'available_packages': PackageSerializer(available_packages, many=True).data
        })
        
    except Exception as e:
        logger.error(f"Error fetching user packages: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error fetching package information'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_package_usage(request):
    """
    Get current package usage statistics
    """
    try:
        current_package = UserPackage.objects.filter(
            user=request.user,
            status='active'
        ).select_related('package').first()
        
        if not current_package or not current_package.is_active():
            return Response({
                'success': False,
                'message': 'No active package found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        usage, created = PackageFeatureUsage.objects.get_or_create(
            user_package=current_package
        )
        
        return Response({
            'success': True,
            'package': PackageSerializer(current_package.package).data,
            'usage': PackageFeatureUsageSerializer(usage).data,
            'remaining_days': current_package.get_remaining_days()
        })
        
    except Exception as e:
        logger.error(f"Error fetching package usage: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error fetching usage information'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def activate_package_after_payment(user_package_id, transaction_data=None):
    """
    Helper function to activate package after successful payment
    This will be called from EPS callback
    """
    try:
        user_package = UserPackage.objects.get(id=user_package_id)
        
        # Activate the package
        user_package.activate_package()
        
        # Store payment gateway response
        if transaction_data:
            user_package.payment_gateway_response = transaction_data
            user_package.save()
        
        # Create feature usage record
        PackageFeatureUsage.objects.get_or_create(
            user_package=user_package
        )
        
        logger.info(f"Package activated: User {user_package.user.id}, Package {user_package.package.id}")
        
        return True
        
    except UserPackage.DoesNotExist:
        logger.error(f"UserPackage not found: {user_package_id}")
        return False
    except Exception as e:
        logger.error(f"Error activating package: {str(e)}")
        return False
