from django.shortcuts import render
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import permissions

from globalapp.views import BaseViews
from users.permissions import IsStaff
from phonebook.models import Phone
from phonebook.serializers import PhoneSerializer

# Create your views here.
class PhoneViewSet(BaseViews):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated,IsStaff]
    model_name =Phone
    methods = ["list", "retrieve", "create", "update", "partial_update", "destroy", "soft_delete", "change_status", "restore_soft_deleted"]
    queryset = Phone.objects.all()
    serializer_class = PhoneSerializer