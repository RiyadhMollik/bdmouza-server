"""
Package API Views
"""
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
import logging

from .models import Package, UserPackage, PackageFeatureUsage, DailyOrderUsage
from .serializers import (
    PackageSerializer, 
    UserPackageSerializer, 
    PackagePurchaseSerializer,
    UserProfilePackageSerializer,
    PackageFeatureUsageSerializer,
    DailyOrderUsageSerializer,
    DailyOrderStatusSerializer
)
from others.models import Purchases

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
        
        # Only check if user already has an ACTIVE package of the same type
        existing_active = UserPackage.objects.filter(
            user=request.user,
            package=package,  # Check for the exact same package
            status='active'
        ).first()
        
        if existing_active and existing_active.is_active():
            return Response({
                'success': False,
                'message': f'You already have an active {package.name} package'
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
                'order_type': 'package',  # Specify order type as package
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
        # Get current active package (only show successful/active packages)
        current_package = UserPackage.objects.filter(
            user=request.user,
            status='active'
        ).select_related('package').first()
        
        if current_package and not current_package.is_active():
            current_package = None
        
        # Get package history - only show successful packages
        package_history = UserPackage.objects.filter(
            user=request.user,
            status__in=['active', 'expired', 'completed']  # Only show successful packages
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
        logger.info(f"🔄 Attempting to activate package with user_package_id: {user_package_id}")
        
        user_package = UserPackage.objects.get(id=user_package_id)
        logger.info(f"📦 Found UserPackage: {user_package.id} for user {user_package.user.email}")
        
        # Activate the package
        user_package.activate_package()
        logger.info(f"✅ Package activated successfully: {user_package.status}")
        
        # Store payment gateway response
        if transaction_data:
            user_package.payment_gateway_response = transaction_data
            user_package.save()
            logger.info(f"💾 Saved transaction data for package {user_package.id}")
        
        # Create feature usage record
        PackageFeatureUsage.objects.get_or_create(
            user_package=user_package
        )
        logger.info(f"📊 Created feature usage record for package {user_package.id}")
        
        logger.info(f"🎉 Package activation completed: User {user_package.user.id}, Package {user_package.package.id}")
        
        return True
        
    except UserPackage.DoesNotExist:
        logger.error(f"❌ UserPackage not found with ID: {user_package_id}")
        return False
    except Exception as e:
        logger.error(f"❌ Error activating package {user_package_id}: {str(e)}", exc_info=True)
        return False


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_daily_order_status(request):
    """
    Get user's daily order status for current active package
    """
    try:
        # Get user's current active package
        current_package = UserPackage.objects.filter(
            user=request.user,
            status='active'
        ).select_related('package').first()
        
        if not current_package or not current_package.is_active():
            return Response({
                'success': False,
                'message': 'No active package found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get daily order status
        daily_status = current_package.get_daily_order_status()
        daily_status['package_name'] = current_package.package.name
        daily_status['package_type'] = current_package.package.package_type
        
        serializer = DailyOrderStatusSerializer(daily_status)
        
        return Response({
            'success': True,
            'daily_order_status': serializer.data
        })
        
    except Exception as e:
        logger.error(f"Error fetching daily order status: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error fetching daily order status'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_order_limit(request):
    """
    Validate if user can place an order today and reserve slots if possible
    """
    try:
        # Get file count from request data
        file_count = request.data.get('file_count', 1)
        if not isinstance(file_count, int) or file_count < 1:
            file_count = 1
        
        # Get user's current active package
        current_package = UserPackage.objects.filter(
            user=request.user,
            status='active'
        ).select_related('package').first()
        
        if not current_package or not current_package.is_active():
            return Response({
                'success': False,
                'can_order': False,
                'message': 'No active package found'
            }, status=status.HTTP_200_OK)
        
        # Check if user can order today with the specified file count
        can_order = current_package.can_order_today(file_count=file_count)
        daily_status = current_package.get_daily_order_status()
        
        if can_order:
            # Reserve slots by incrementing usage with file count
            success = current_package.increment_daily_order_usage(file_count=file_count)
            if success:
                # Get updated status
                updated_status = current_package.get_daily_order_status()
                
                return Response({
                    'success': True,
                    'can_order': True,
                    'message': f'Order slots reserved successfully for {file_count} files',
                    'is_free_order': True,
                    'file_count': file_count,
                    'daily_order_status': {
                        **updated_status,
                        'package_name': current_package.package.name,
                        'package_type': current_package.package.package_type
                    }
                })
            else:
                return Response({
                    'success': False,
                    'can_order': False,
                    'message': 'Failed to reserve order slot'
                })
        else:
            return Response({
                'success': True,
                'can_order': False,
                'is_free_order': False,
                'message': 'Daily order limit reached. This will be a paid order.',
                'daily_order_status': {
                    **daily_status,
                    'package_name': current_package.package.name,
                    'package_type': current_package.package.package_type
                }
            })
        
    except Exception as e:
        logger.error(f"Error validating order limit: {str(e)}")
        return Response({
            'success': False,
            'can_order': False,
            'message': 'Error validating order limit'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_daily_usage_history(request):
    """
    Get user's daily order usage history
    """
    try:
        # Get user's current active package
        current_package = UserPackage.objects.filter(
            user=request.user,
            status='active'
        ).select_related('package').first()
        
        if not current_package:
            return Response({
                'success': False,
                'message': 'No active package found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get usage history for last 30 days
        from datetime import timedelta
        from django.utils import timezone
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        
        usage_history = DailyOrderUsage.objects.filter(
            user_package=current_package,
            date__gte=thirty_days_ago
        ).order_by('-date')
        
        serializer = DailyOrderUsageSerializer(usage_history, many=True)
        
        return Response({
            'success': True,
            'usage_history': serializer.data,
            'package_info': {
                'name': current_package.package.name,
                'daily_limit': current_package.package.daily_order_limit,
                'is_unlimited': current_package.package.daily_order_limit == 0
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching usage history: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error fetching usage history'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cleanup_pending_packages(request):
    """
    Cleanup old pending packages (older than 1 hour)
    """
    try:
        from django.utils import timezone
        from datetime import timedelta
        
        # Delete pending packages older than 1 hour
        one_hour_ago = timezone.now() - timedelta(hours=1)
        old_pending = UserPackage.objects.filter(
            user=request.user,
            status='pending',
            created_at__lt=one_hour_ago
        )
        
        count = old_pending.count()
        old_pending.delete()
        
        return Response({
            'success': True,
            'message': f'Cleaned up {count} old pending packages',
            'deleted_count': count
        })
        
    except Exception as e:
        logger.error(f"Error cleaning up pending packages: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error cleaning up pending packages'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_free_order(request):
    """
    Process a free order that's within daily limits
    """
    try:
        # Get request data
        file_names = request.data.get('file_name', [])
        file_count = request.data.get('file_count', len(file_names) if file_names else 1)
        package_id = request.data.get('package')
        checkout_type = request.data.get('checkout_type', 'file_based')
        
        # Validation
        if not package_id:
            return Response({
                'success': False,
                'message': 'Package ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not isinstance(file_count, int) or file_count < 1:
            file_count = 1
        
        # Get user's current active package
        current_package = UserPackage.objects.filter(
            user=request.user,
            status='active'
        ).select_related('package').first()
        
        if not current_package or not current_package.is_active():
            return Response({
                'success': False,
                'message': 'No active package found'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # For free orders, we use the user's current active package
        # No need to verify package match since free orders can only use active package
        logger.info(f"Processing free order for user {request.user.id} with package {current_package.package.id} ({current_package.package.name})")
        
        # Check if user can still order today
        can_order = current_package.can_order_today(file_count=file_count)
        if not can_order:
            return Response({
                'success': False,
                'message': 'Daily limit exceeded'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Process the free order by consuming daily limits
        success = current_package.increment_daily_order_usage(file_count=file_count)
        if not success:
            return Response({
                'success': False,
                'message': 'Failed to process free order'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Create a Purchases record for the free order so it appears in user-files
        try:
            # Get the PackageItem that corresponds to this package
            from others.models import PackageItem
            package_item = PackageItem.objects.filter(
                field_name=current_package.package.name
            ).first()
            
            purchase = Purchases.objects.create(
                user=request.user,
                package=package_item,  # This can be None if not found
                file_name=file_names,
                payment_status='completed',  # Mark as completed for free orders
                amount=0,  # Free order amount
                payment_method='free',  # Indicate this was a free order
                mobile_number=request.data.get('mobile_number', ''),
                note=f"Free order processed on {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            logger.info(f"Created Purchases record {purchase.id} for free order")
            
        except Exception as e:
            logger.error(f"Failed to create Purchases record for free order: {str(e)}")
            # Don't fail the entire request if purchase record creation fails
        
        # Create order record for tracking (you might want to create an Order model)
        order_data = {
            'user_id': request.user.id,
            'package_id': current_package.package.id,  # Use current active package ID
            'file_names': file_names,
            'file_count': file_count,
            'amount': 0,
            'is_free_order': True,
            'checkout_type': checkout_type,
            'status': 'completed',
            'processed_at': timezone.now().isoformat()
        }
        
        # Get updated status
        updated_status = current_package.get_daily_order_status()
        
        logger.info(f"Free order processed successfully for user {request.user.id}: {file_count} files")
        
        return Response({
            'success': True,
            'message': f'Free order processed successfully for {file_count} files',
            'order_data': order_data,
            'daily_order_status': {
                **updated_status,
                'package_name': current_package.package.name,
                'package_type': current_package.package.package_type
            }
        })
        
    except Exception as e:
        logger.error(f"Error processing free order: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error processing free order'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
