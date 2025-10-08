from django.shortcuts import render
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import permissions
from django.contrib.auth.models import Group, Permission
from rest_framework import status
from users.permissions import IsStaff
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import filters
try:
    from globalapp.ed import encode_jwt
except:
    pass
from globalapp.views import BaseViews
from users.models import Roles, Users
from users.serializers import AllUserSerializer, CustomTokenObtainPairSerializer, GropuSerializer, PermissionSerializer, RolesSerializer, UserSerializer
# Create your views here.
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class =CustomTokenObtainPairSerializer
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        token=response.data['access']
        payload = AccessToken(token).payload
        user_id = payload.get('user_id')
        user = Users.objects.filter(id=user_id)
        serializer = AllUserSerializer(user, many=True)
        for user_data in serializer.data:
            if 'roles' in user_data:
                for role in user_data['roles']['menu']:
                    if 'permissions' in role:
                        for permission in role['permissions']:
                            permission['submenu'] = permission['codename'].split('_')[1]
                            permission['access'] = permission['codename'].split('_')[0]
        
        serializer.instance = user
        try:
            response.data["user"] = encode_jwt({"data": serializer.data})

        except:
            response.data["user"] = {"data": serializer.data}
        return response

class RoleViewSet(BaseViews):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated,IsStaff]
    model_name = Roles
    methods=["list", "retrieve", "create", "update", "partial_update", "destroy", "soft_delete", "change_status", "restore_soft_deleted"]
    queryset = Roles.objects.all()
    serializer_class = RolesSerializer

class GroupViewSet(BaseViews):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated,IsStaff]
    model_name = Group
    
    methods=["list", "retrieve", "create", "update", "partial_update", "destroy", "soft_delete", "change_status", "restore_soft_deleted"]
    serializer_class = GropuSerializer

class PermissionViewSet(BaseViews):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated,IsStaff]
    model_name = Permission
    
    methods=["list", "retrieve", "create", "update", "partial_update", "destroy", "soft_delete", "change_status", "restore_soft_deleted"]
    serializer_class = PermissionSerializer
    def list(self, request, *args, **kwargs):
        if "list" in self.methods:
            try:
                limit = request.GET.get('limit')
            except:
                limit = None
            if limit is None:
                # No limit parameter provided, return all data
                
                queryset = self.filter_queryset(self.get_queryset())
                # print(self.get_queryset())
                serializer = self.get_serializer(queryset, many=True)
                for data in serializer.data:
                    data['access'] = data['codename'].split('_')[0]
                    # print(data)

                token = encode_jwt({"data": serializer.data})  # Encode serialized data into JWT token
                return self.generate_response(True, status.HTTP_200_OK, "list_success", data={"token": token})
            else:
                # Pagination requested, apply pagination
                queryset = self.filter_queryset(self.get_queryset())
                page = self.paginate_queryset(queryset)
                if page is not None:
                    serializer = self.get_serializer(page, many=True)
                    for data in serializer.data:
                        data['access'] = data['codename'].split('_')[0]
                    # print(data)
                    token = encode_jwt({"data": serializer.data})  # Encode serialized data into JWT token
                    return self.get_paginated_response({"token": token})
        else:
            return self.generate_response(False, status.HTTP_405_METHOD_NOT_ALLOWED, "list_not_allowed")
        
class UserViewSet(BaseViews):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated,IsStaff]
    model_name = Users
    methods=["list", "retrieve", "create", "update", "partial_update", "destroy", "soft_delete", "change_status", "restore_soft_deleted"]
    serializer_class = UserSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['roles__name']  # Enable filtering by role name
    def get_permissions(self):
        # Allow list and create actions without authentication
        if self.action in ['list', 'create']:
            return [permissions.AllowAny()]
        if self.action in ['update_profile', 'get_own_data']:
            return [permissions.IsAuthenticated()]
        # For other actions, staff permission is required
        return super().get_permissions()
        
    @action(detail=True, methods=['patch'], permission_classes=[permissions.IsAuthenticated])
    def update_profile(self, request, pk=None):
        # If user is a staff member, they can update anyone's profile
        if request.user.is_staff:
            user = Users.objects.get(pk=pk)
        else:
            # Non-staff users can only update their own profile
            user = request.user
        print(request.data)
        serializer = UserSerializer(user, data=request.data, partial=True, context={'request': request})
        
        
        if serializer.is_valid():
            serializer.save()
            
            token = encode_jwt({"data": serializer.data})
            return self.generate_response(True, status.HTTP_201_CREATED, "create_success", data={"token": token})
        else:
            print(f"Validation failed for phone number: {request.data.get('phone_number')}")
            print(serializer.errors)  # Log detailed errors
        return self.generate_response(False, status.HTTP_405_METHOD_NOT_ALLOWED, "list_not_allowed")
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def get_own_data(self, request):
        user = request.user
        serializer = UserSerializer(user, partial=True, context={'request': request})
        token = encode_jwt({"data": serializer.data})
        return self.generate_response(
            True,
            status.HTTP_200_OK,
            "user_data_retrieved",
            data={"token": token}
        )

##google sign in
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from users.models import Users

class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        id_token = request.data.get('token')
        if not id_token:
            return Response({"detail": "Token is required."}, status=status.HTTP_400_BAD_REQUEST)

        google_verify_url = "https://oauth2.googleapis.com/tokeninfo"
        response = requests.get(google_verify_url, params={"id_token": id_token})

        if response.status_code != 200:
            return Response({"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

        user_data = response.json()
        email = user_data.get("email")
        name = user_data.get("name", "")
        picture = user_data.get("picture", "")

        if not email:
            return Response({"detail": "No email in token."}, status=status.HTTP_400_BAD_REQUEST)

        user, created = Users.objects.get_or_create(email=email, defaults={
            "name": name,
            "is_verified": True,
        })
        if created:
            user.set_unusable_password()
            user.save()

        refresh = RefreshToken.for_user(user)

        # ✅ Return full encoded user info (just like normal login)
        user_qs = Users.objects.filter(id=user.id)
        serializer = AllUserSerializer(user_qs, many=True)
        for user_data in serializer.data:
            if 'roles' in user_data:
                for role in user_data['roles']['menu']:
                    if 'permissions' in role:
                        for permission in role['permissions']:
                            permission['submenu'] = permission['codename'].split('_')[1]
                            permission['access'] = permission['codename'].split('_')[0]
        try:
            encoded_user_data = encode_jwt({"data": serializer.data})
        except:
            encoded_user_data = {"data": serializer.data}

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": encoded_user_data
        }, status=200)

#forget pass:
import jwt
from datetime import datetime, timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.urls import reverse

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from users.models import Users

class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"detail": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = Users.objects.get(email=email)
        except Users.DoesNotExist:
            return Response({"detail": "User not found."}, status=404)

        token = jwt.encode({
            'user_id': user.id,
            'exp': datetime.utcnow() + timedelta(minutes=30)
        }, settings.SECRET_KEY, algorithm='HS256')

        reset_link = request.build_absolute_uri(f"/reset-password/?token={token}")

        # ✅ HTML Email Template
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #ddd; padding: 30px;">
            <h2 style="color: #1a73e8;">Reset Your Password</h2>
            <p>Hello <strong>{user.name or user.email}</strong>,</p>
            <p>You requested to reset your password. Click the button below to continue:</p>
            <p style="text-align: center; margin: 20px 0;">
                <a href="{reset_link}" style="background-color: #1a73e8; color: white; padding: 12px 20px; text-decoration: none; border-radius: 5px;">
                    Reset Password
                </a>
            </p>
            <p>If you didn’t request this, just ignore this email.</p>
            <p style="margin-top: 30px;">Thanks,<br><strong>BD Mouza Team</strong></p>
        </div>
        """

        send_mail(
            subject='Reset Your Password - BD Mouza',
            message='Click the link below to reset your password:\n' + reset_link,
            from_email=f'BD Mouza <{settings.DEFAULT_FROM_EMAIL}>',
            recipient_list=[user.email],
            fail_silently=False,
            html_message=html_content,
        )

        return Response({"detail": "Password reset link sent to your email."}, status=200)


class ResetPasswordFormView(View):
    def get(self, request):
        token = request.GET.get("token")
        return render(request, "users/reset_password_form.html", {"token": token})

    def post(self, request):
        token = request.POST.get("token")
        new_password = request.POST.get("password")

        if not token or not new_password:
            messages.error(request, "Token and password are required.")
            return redirect('/reset-password/?token=' + token)

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user = Users.objects.get(id=payload['user_id'])
            user.set_password(new_password)
            user.save()
            messages.success(request, "Password reset successful.")
            return redirect('https://bdmouza.com/login')  # ✅ Redirect to your site
        except jwt.ExpiredSignatureError:
            messages.error(request, "Token has expired.")
        except Exception as e:
            messages.error(request, "Invalid or expired link.")
        return redirect('/reset-password/')
        
#loguout view
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"detail": "Logout successful."}, status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response({"detail": "Invalid refresh token."}, status=status.HTTP_400_BAD_REQUEST)
            
            
#google signup
# users/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from users.models import Users, Roles
import requests
from globalapp.ed import encode_jwt  # Optional JWT encoding for full user data

class GoogleSignupView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        id_token = request.data.get('token')
        if not id_token:
            return Response({"detail": "Token is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Verify token with Google
        google_verify_url = "https://oauth2.googleapis.com/tokeninfo"
        response = requests.get(google_verify_url, params={"id_token": id_token})

        if response.status_code != 200:
            return Response({"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

        user_data = response.json()
        email = user_data.get("email")
        name = user_data.get("name", "")
        picture = user_data.get("picture", "")

        if not email:
            return Response({"detail": "No email found in token."}, status=status.HTTP_400_BAD_REQUEST)

        # If user already exists, return error
        if Users.objects.filter(email=email).exists():
            return Response({"detail": "User already exists. Please login."}, status=status.HTTP_400_BAD_REQUEST)

        # Create new user
        default_role = Roles.objects.filter(id=42659).first()  # optional default role
        user = Users.objects.create(
            email=email,
            name=name,
            is_verified=True,
            roles=default_role
        )
        user.set_unusable_password()
        user.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        # Encode full user data if needed
        user_qs = Users.objects.filter(id=user.id)
        from users.serializers import AllUserSerializer
        serializer = AllUserSerializer(user_qs, many=True)
        try:
            encoded_user_data = encode_jwt({"data": serializer.data})
        except:
            encoded_user_data = {"data": serializer.data}

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": encoded_user_data
        }, status=201)
