from django.shortcuts import render
import httpx
# Create your views here.
# views.py
from rest_framework import viewsets
from rest_framework.decorators import action
from globalapp.views import BaseViews
from others.models import ExtraFeature, Package, PackageItem, Purchases, Tutorial, UddoktapayConfiguration
from others.serializers import PackageItemSerializer, PackageSerializer, PurchaseSerializer, TutorialSerializer
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from django.views.generic import TemplateView
from users.models import Users, Roles
from .serializers import ExtraFeatureSerializer, PurchaseSerializer
from .helpers import BkashPaymentHelper,UddoktapayPaymentHelper  # if you put helper in helpers.py
from django.contrib.auth import authenticate, get_user_model
import requests

class PackageItemViewSet(BaseViews):
    model_name = PackageItem
    methods = ["list", "retrieve"]
    queryset = PackageItem.objects.all()
    serializer_class = PackageItemSerializer
class PackageViewSet(BaseViews):
    model_name = Package
    methods = ["list", "retrieve"]
    queryset = Package.objects.all()
    serializer_class = PackageSerializer

class TutorialViewSet(BaseViews):
    model_name = Tutorial
    methods = ["list", "retrieve"]
    queryset = Tutorial.objects.all()
    serializer_class = TutorialSerializer
class ExtraFeatureViewSet(BaseViews):
    model_name = ExtraFeature
    methods = ["list", "retrieve"]
    queryset = ExtraFeature.objects.all()
    serializer_class = ExtraFeatureSerializer
class PurchaseViewSet(BaseViews):
    model_name = Purchases
    methods = ["list", "retrieve", "create"]
    queryset = Purchases.objects.all()
    serializer_class = PurchaseSerializer

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        user = request.user if request.user.is_authenticated else None

        if not user:
            email = data.get("email")
            password = data.get("password")

            if not email or not password:
                return Response(
                    {"error": "Email and password are required for unauthenticated users."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Try to authenticate an existing user
            user = authenticate(request, email=email, password=password)

            if not user:
                # If email exists but password is wrong
                if Users.objects.filter(email=email).exists():
                    return Response(
                        {"error": "Invalid password for existing user."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # If new user, create one using your custom manager
                user = Users.objects.create_user(email=email, password=password)

        # Inject the user ID into data
        data["user"] = user.id

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        purchase = serializer.save(user=user)

        # Create bKash payment
        amount = data.get("amount")
        invoice = f"INV-{purchase.id}-{user.id}"
        bkash = BkashPaymentHelper()
        bkash_url, payment_id = bkash.create_payment(amount, invoice)

        if bkash_url and payment_id:
            purchase.number = payment_id
            purchase.save()
            return Response({
                "payment_url": bkash_url,
                "payment_id": payment_id,
                "purchase_id": purchase.id,
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                "error": "Failed to initiate bKash payment."
            }, status=status.HTTP_400_BAD_REQUEST)
        
class UddoktapayPurchaseViewSet(BaseViews):
    model_name = Purchases
    methods = ["list", "retrieve", "create"]
    queryset = Purchases.objects.all()
    serializer_class = PurchaseSerializer

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        user = request.user if request.user.is_authenticated else None

        if not user:
            email = data.get("email")
            password = data.get("password")

            if not email or not password:
                return Response(
                    {"error": "Email and password are required for unauthenticated users."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user = authenticate(request, email=email, password=password)

            if not user:
                if Users.objects.filter(email=email).exists():
                    return Response(
                        {"error": "Invalid password for existing user."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                # Create user
                user = Users.objects.create_user(email=email, password=password)

                # Assign default role (foreign key)
                try:
                    default_role = Roles.objects.get(id=42659)
                    user.roles = default_role
                    user.save()
                except Roles.DoesNotExist:
                    return Response(
                        {"error": "Default role not found."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        data["user"] = user.id
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        purchase = serializer.save(user=user)

        # Create Uddoktapay payment
        amount = data.get("amount")
        full_name = user.username or "Unnamed"
        email = user.email
        order_id = purchase.id

        uddoktapay = UddoktapayPaymentHelper()
        payment_url = uddoktapay.create_payment(full_name, email, amount, user.id, order_id)

        if payment_url:
            return Response({
                "payment_url": payment_url,
                "purchase_id": purchase.id
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                "error": "Failed to initiate Uddoktapay payment."
            }, status=status.HTTP_400_BAD_REQUEST)
    @action(detail=False, methods=["post"], url_path="validate")
    def validate_payment(self, request):
        invoice_id = request.data.get("invoice_id")
        if not invoice_id:
            return Response({"error": "invoice_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        config = UddoktapayConfiguration.objects.first()
        if not config or not config.api_key:
            return Response({"error": "Payment configuration missing."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        api_key = config.api_key
        url = (
            "https://sandbox.uddoktapay.com/api/verify-payment"
            if config.sandbox else
            "https://pay.bdmouza.com/api/verify-payment"
        )

        headers = {
            "accept": "application/json",
            "RT-UDDOKTAPAY-API-KEY": api_key,
            "content-type": "application/json",
            "User-Agent": "Thunder Client"
        }

        try:
            with httpx.Client(http2=False, verify=False, timeout=15) as client:
                response = client.post(url, headers=headers, json={"invoice_id": invoice_id})
                print("[Raw Response]", response.text)
                data = response.json()
                print("[Uddoktapay Response]", data)

                if data.get("status") == "COMPLETED" and data.get("metadata", {}).get("user_id"):
                    user_id = data["metadata"]["user_id"]

                    # Get latest purchase for this user
                    purchase = Purchases.objects.filter(user_id=user_id).order_by('-id').first()
                    if not purchase:
                        return Response({"error": "No purchases found for this user."}, status=status.HTTP_404_NOT_FOUND)

                    purchase.trx_number = data["invoice_id"]
                    purchase.payment_status = 'completed'
                    purchase.save()

                    print(f"[INFO] Payment validated. Invoice: {data['invoice_id']} → Purchase ID: {purchase.id}")

                    return Response({
                        "success": True,
                        "message": "Payment validated and latest purchase updated.",
                        "invoice_id": data["invoice_id"],
                        "purchase_id": purchase.id
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({"error": "Invalid or incomplete payment."}, status=status.HTTP_400_BAD_REQUEST)

        except httpx.HTTPError as e:
            print("[ERROR] HTTPX error while validating payment:", e)
            return Response({"error": "Payment validation failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
      
class PaymentSuccessView(TemplateView):
    template_name = "others/success.html"

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     context["invoice_id"] = self.request.GET.get("invoice_id", "N/A")
    #     context["purchase_id"] = self.request.GET.get("purchase_id", "N/A")
    #     return context
    
#alt view:

class PurchaseViewSet2(BaseViews):
    queryset = Purchases.objects.all()
    serializer_class = PurchaseSerializer

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        user = request.user if request.user.is_authenticated else None

        if not user:
            email = data.get("email")
            password = data.get("password")

            if not email or not password:
                return Response(
                    {"error": "Email and password are required for unauthenticated users."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user = authenticate(request, email=email, password=password)

            if not user:
                if Users.objects.filter(email=email).exists():
                    return Response(
                        {"error": "Invalid password for existing user."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                user = Users.objects.create_user(email=email, password=password)

                try:
                    default_role = Roles.objects.get(id=42659)
                    user.roles = default_role
                    user.save()
                except Roles.DoesNotExist:
                    return Response(
                        {"error": "Default role not found."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        data["user"] = user.id
        payment_method = data.get("payment_method", "bkash").lower()

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        purchase = serializer.save(user=user)

        amount = data.get("amount")
        full_name = user.username or "Unnamed"
        email = user.email
        order_id = purchase.id

        if payment_method == "others":
            # Uddoktapay Logic
            uddoktapay = UddoktapayPaymentHelper()
            payment_url = uddoktapay.create_payment(full_name, email, amount, user.id, order_id)

            if payment_url:
                return Response({
                    "payment_method": "others",
                    "payment_url": payment_url,
                    "purchase_id": purchase.id
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    "error": "Failed to initiate Uddoktapay payment."
                }, status=status.HTTP_400_BAD_REQUEST)

        elif payment_method == "eps":
            # EPS Payment Logic
            print("🧪 Testing create_eps_payment function...")
            try:
                from epspayment.utils import create_eps_payment
                
                # Prepare EPS payment data
                eps_payment_data = {
                    'amount': float(amount),
                    'customer_name': full_name,
                    'customer_email': email or 'unknown@example.com',
                    'customer_phone': user.phone_number if hasattr(user, 'phone_number') else '',
                    'order_id': f"ORD-{purchase.id}-{user.id}",
                    'description': f"Purchase #{purchase.id}",
                    'user_id': user.id,
                    'purchase_id': purchase.id
                }
                
                eps_result = create_eps_payment(eps_payment_data)
                
                if eps_result.get('success'):
                    # Store transaction ID in purchase
                    purchase.trx_number = eps_result.get('transaction_id')
                    purchase.save()
                    
                    return Response({
                        "payment_method": "eps",
                        "payment_url": eps_result.get('payment_url'),
                        "purchase_id": purchase.id,
                        "transaction_id": eps_result.get('transaction_id')
                    }, status=status.HTTP_201_CREATED)
                else:
                    return Response({
                        "error": eps_result.get('message', 'Failed to initiate EPS payment.')
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except ImportError:
                return Response({
                    "error": "EPS payment service not available."
                }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({
                    "error": f"EPS payment error: {str(e)}"
                }, status=status.HTTP_400_BAD_REQUEST)

        else:
            # bKash Logic (default)
            bkash = BkashPaymentHelper()
            invoice = f"INV-{purchase.id}-{user.id}"
            bkash_url, payment_id = bkash.create_payment(amount, invoice)

            if bkash_url and payment_id:
                purchase.trx_number = payment_id
                purchase.save()
                return Response({
                    "payment_method": "bkash",
                    "payment_url": bkash_url,
                    "purchase_id": purchase.id
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    "error": "Failed to initiate bKash payment."
                }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"], url_path="validate")
    def validate_payment(self, request):
        invoice_id = request.data.get("invoice_id")
        payment_id = request.data.get("payment_id")
        status_val = request.data.get("status")

        # ✅ Case 1: Handle Uddoktapay invoice validation
        if invoice_id:
            config = UddoktapayConfiguration.objects.first()
            if not config or not config.api_key:
                return Response({"error": "Payment configuration missing."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            api_key = config.api_key
            url = (
                "https://sandbox.uddoktapay.com/api/verify-payment"
                if config.sandbox else
                "https://pay.bdmouza.com/api/verify-payment"
            )

            headers = {
                "accept": "application/json",
                "RT-UDDOKTAPAY-API-KEY": api_key,
                "content-type": "application/json",
                "User-Agent": "Thunder Client"
            }

            try:
                with httpx.Client(http2=False, verify=False, timeout=15) as client:
                    response = client.post(url, headers=headers, json={"invoice_id": invoice_id})
                    data = response.json()

                    if data.get("status") == "COMPLETED" and data.get("metadata", {}).get("user_id"):
                        user_id = data["metadata"]["user_id"]
                        purchase = Purchases.objects.filter(user_id=user_id).order_by('-id').first()
                        if not purchase:
                            return Response({"error": "No purchases found for this user."}, status=status.HTTP_404_NOT_FOUND)

                        purchase.trx_number = data["invoice_id"]
                        purchase.payment_status = 'completed'
                        purchase.save()

                        return Response({
                            "success": True,
                            "message": "Payment validated and latest purchase updated.",
                            "invoice_id": data["invoice_id"],
                            "purchase_id": purchase.id
                        }, status=status.HTTP_200_OK)
                    else:
                        return Response({"error": "Invalid or incomplete payment."}, status=status.HTTP_400_BAD_REQUEST)

            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # ✅ Case 2: Handle bKash execution after frontend callback
        elif payment_id and status_val == "success":
            purchase = Purchases.objects.filter(trx_number=payment_id).first()
            if not purchase:
                return Response({"error": "No purchase found with this transaction number."}, status=status.HTTP_404_NOT_FOUND)

            # Execute bKash payment
            bkash = BkashPaymentHelper()
            result = bkash.execute_payment(payment_id)
            print("bKash execute result:", result)

            if result.get("transactionStatus") == "Completed":
                purchase.payment_status = "completed"
                purchase.save()

                return Response({
                    "success": True,
                    "message": "bKash payment executed and confirmed.",
                    "purchase_id": purchase.id,
                    "payment_id": payment_id
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "error": "bKash payment execution failed or incomplete.",
                    "bkash_response": result
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response({"error": "Required fields missing."}, status=status.HTTP_400_BAD_REQUEST)