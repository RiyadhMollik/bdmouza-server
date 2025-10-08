from django.shortcuts import render
from rest_framework import permissions,status
from globalapp.views import BaseViews
from lmsfeatures.models import Courses, EnrollCourse, InstallationStatus, Payment, PaymentMethods, SSLcommerceSettings
from lmsfeatures.serializers import CourseSerializer, EnrollCourseSerializer, InstallationStatusSerializer, PaymentMethodsSerializer, PaymentSerializer, SSLcommerceSettingsSerializer
from rest_framework.response import Response
# from django.contrib.auth.models import User
from globalapp.ed import encode_jwt
from users.models import Users
from django.contrib.auth.hashers import make_password
from sslcommerz_lib import SSLCOMMERZ
# Create your views here.
class CoursesViewSet(BaseViews):
    model_name = Courses
    methods = ["list", "retrieve", "create", "update", "partial_update", "destroy", "soft_delete", "change_status", "restore_soft_deleted"]
    queryset = Courses.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'slug'
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            self.permission_classes = [permissions.AllowAny]
        else:
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()
    
class PaymentViewSet(BaseViews):
    model_name = Payment
    methods = ["list", "retrieve", "create", "update", "partial_update", "destroy", "soft_delete", "change_status", "restore_soft_deleted"]
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_permissions(self):
        # Allow 'list' and 'create' actions without authentication
        if self.action in ['create']:
            return [permissions.AllowAny()]
        # Require authentication for all other actions
        return [permissions.IsAuthenticated()]
    def create(self, request, *args, **kwargs):
        if "create" in self.methods:
            # Get payment method from the request
            payment_way = request.data.get('payment_way')

            # If user is authenticated, proceed directly
            print(request)
            if request.user.is_authenticated:
                user = request.user
            else:
                # Check if the email and password are provided for creating a new user
                email = request.data.get('email')
                password = request.data.get('password')

                if email and password:
                    user, created = Users.objects.get_or_create(email=email, defaults={'password': make_password(password)})
                else:
                    return self.generate_response(False, status.HTTP_400_BAD_REQUEST, "create_validation_error", error="Email and password are required for user creation")

            # Set the user in the payment data
            request.data['user_id'] = user.id

            if payment_way == 'manual':
                return self.create_manual_payment(request)
            elif payment_way == 'sslcommerz':
                return self.create_sslcommerz_payment(request,user)
            else:
                return self.generate_response(False, status.HTTP_400_BAD_REQUEST, "create_validation_error", error="Invalid payment method")

        else:
            return self.generate_response(False, status.HTTP_405_METHOD_NOT_ALLOWED, "create_not_allowed")

    def create_manual_payment(self, request):
        # Handle manual payment
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            token = encode_jwt({"data": serializer.data})
            return self.generate_response(True, status.HTTP_201_CREATED, "create_success", data={"token": token})
        except Exception as e:
            return self.generate_response(False, status.HTTP_400_BAD_REQUEST, "create_validation_error", error=str(e))

    def create_sslcommerz_payment(self, request,user):
        # Handle SSLCommerz payment
        credentials= SSLcommerceSettings.objects.get(pk=1)
        print(credentials.store_id)
        sslcommerz = SSLCOMMERZ({
            'store_id': credentials.store_id,
            'store_pass': credentials.store_pass,
            'issandbox': credentials.sandbox_status  # Set to False for production
        })
        
        print(user.address or "")
        course = Courses.objects.get(pk=request.data.get('course_id'))
        print(course)

        payment_data = {
            'total_amount': request.data.get('amount'),
            'currency': 'BDT',
            'tran_id': request.data.get('transaction_id'),  # You can generate a unique transaction ID
            'success_url': 'https://yourdomain.com/payment-success',
            'fail_url': 'https://yourdomain.com/payment-fail',
            'cancel_url': 'https://yourdomain.com/payment-cancel',
            'cus_name': user.name,
            'cus_email': user.email,
            'cus_add1': user.address or "",
            'cus_city': 'City',
            'cus_country': 'Bangladesh',
            'ship_name': 'Shipping Name',
            'ship_add1': 'Shipping Address',
            'ship_city': 'Shipping City',
            'ship_country': 'Bangladesh',
            "cus_phone": str(user.phone_number),
            "shipping_method": 'No',
            "product_name": course.title,
            "product_category": "Course",
            'product_profile': "non-physical-goods"

        }

        response = sslcommerz.createSession(payment_data)

        if response['status'] == 'SUCCESS':
            print(request.data['user_id'])
            Payment.objects.create(
                user_id=Users.objects.get(pk=request.data['user_id']),
                course_id = Courses.objects.get(pk=request.data['course_id']),
                payment_type = request.data['payment_type'],
                amount = request.data['amount'],
                number = "SSl Commerz"


            )
            return self.generate_response(True, status.HTTP_200_OK, "create_success", data={"payment_url": response['GatewayPageURL']})
        else:
            return self.generate_response(False, status.HTTP_400_BAD_REQUEST, "create_validation_error", error=response['failedreason'])

    def generate_response(self, success, status_code, message, data=None, error=None):
        response = {
            "success": success,
            "message": message,
        }
        if success and data:
            response['data'] = data
        if not success and error:
            response['error'] = error
        return Response(response, status=status_code)
    

class PaymentMethodsViewSet(BaseViews):
    model_name = PaymentMethods
    methods = ["list", "retrieve", "create", "update", "partial_update", "destroy", "soft_delete", "change_status", "restore_soft_deleted"]
    queryset = PaymentMethods.objects.all()
    serializer_class = PaymentMethodsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            self.permission_classes = [permissions.AllowAny]
        else:
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()
    
class InstallationStatusViewSet(BaseViews):
    model_name = InstallationStatus
    methods = ["list", "retrieve", "create", "update", "partial_update", "destroy", "soft_delete", "change_status", "restore_soft_deleted"]
    queryset = InstallationStatus.objects.all()
    serializer_class = InstallationStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            self.permission_classes = [permissions.AllowAny]
        else:
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()

        #return super().get_permissions()
    
class EnrollCourseViewSet(BaseViews):
    model_name = EnrollCourse
    methods = ["list", "retrieve", "create", "update", "partial_update", "destroy", "soft_delete", "change_status", "restore_soft_deleted"]
    queryset = EnrollCourse.objects.all()
    serializer_class = EnrollCourseSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        # Filter the queryset by the request user's ID
        return EnrollCourse.objects.filter(user_id=self.request.user.id)
    def get_serializer_context(self):
        return {'request': self.request}
    

class SSLcommerceSettingsViewSet(BaseViews):
    model_name = SSLcommerceSettings
    methods = ['list', "retrieve"]
    queryset = SSLcommerceSettings.objects.all()
    serializer_class = SSLcommerceSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            self.permission_classes = [permissions.AllowAny]
        else:
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()
    