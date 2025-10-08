from django.shortcuts import render
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets,parsers
from des.models import DynamicEmailConfiguration
from globalapp.ed import encode_jwt
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination,LimitOffsetPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import FileField, ImageField
from django_filters import rest_framework as filters
from django.db.models import CharField, TextField
from django.utils import timezone
from datetime import datetime
from django.db.models import Q
from django.db import models
from users.permissions import IsStaff
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import permissions
from globalapp.models import SoftwareAsset
from globalapp.serializers import EmailConfigureSerializer, SoftwareAssetSerializer
from rest_framework import serializers
class CustomPagination(LimitOffsetPagination):
    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'status': 200,
            'message': 'Data retrieved successfully',
            'error': None,
            'data': {
                'meta': {
                    'count': self.count,
                    'next': self.get_next_link(),
                    'previous': self.get_previous_link()
                },
                'results': data
            }
        })
    
class CaseInsensitiveCharFilter(filters.CharFilter):
    def filter(self, qs, value):
        if value:
            # Perform a case-insensitive search using 'icontains'
            return qs.filter(**{f"{self.field_name}__icontains": value})
        return qs


class BaseViews(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend]
    # filterset_fields = '__all__'
    # Define message templates
    pagination_class = CustomPagination  # Replace with your custom pagination class if defined
    message_templates = {
        "list_success": "Data retrieved successfully",
        "list_not_allowed": "List method is not allowed",
        "retrieve_success": "Object retrieved successfully",
        "retrieve_not_allowed": "Retrieve method is not allowed",
        "create_success": "Object created successfully",
        "create_validation_error": "Validation error",
        "create_not_allowed": "Create method is not allowed",
        "update_success": "Object updated successfully",
        "update_not_allowed": "Update method is not allowed",
        "partial_update_not_allowed": "Partial Update method is not allowed",
        "destroy_success": "Object deleted successfully",
        "destroy_not_allowed": "Delete method is not allowed",
        "soft_delete_success": "Data deleted. But you can recover your data",
        "soft_delete_not_allowed": "Soft Delete method is not allowed",
        "change_status_success": "Status changed",
        "change_status_not_allowed": "Change Status method is not allowed",
        "restore_soft_deleted_success": "Soft deleted data restored successfully",
        "restore_soft_deleted_not_allowed": "Restore Soft Deleted method is not allowed",
        "leave_count_message": "Count Data get successfully",
        "leave_approve": "Approved Successfully",
        "leave_reject":"Rejected Successfully"
    }


    # Define the custom filter class dynamically
    # def get_queryset(self):
    #     queryset = self.model_name.objects.filter(is_deleted=False)

    #     # Get parameters from the request
    #     params = self.request.query_params

    #     # Iterate through parameters and filter queryset dynamically
    #     for param, value in params.items():
    #         if param in [field.name for field in self.model_name._meta.get_fields()]:
    #             kwargs = {f"{param}__icontains": value}  # Perform case-insensitive partial match
    #             queryset = queryset.filter(Q(**kwargs))
    #         else:
    #             # Check if the parameter corresponds to a field in a related model
    #             related_fields = [field.name for field in self.model_name._meta.get_fields(include_hidden=True) if field.is_relation]
    #             for field_name in related_fields:
    #                 field_object = getattr(self.model_name, field_name)
    #                 if hasattr(field_object, 'related'):
    #                     related_model = field_object.related.related_model
    #                     if param in [related_field.name for related_field in related_model._meta.get_fields()]:
    #                         kwargs = {f"{field_name}__{param}__icontains": value}  # Traverse the relationship
    #                         queryset = queryset.filter(Q(**kwargs))

    #     return queryset.order_by('-id')
    def get_queryset(self):
        try:
            queryset = self.model_name.objects.filter(is_deleted=False)
        except:
            queryset = self.model_name.objects.all()

        # Get parameters from the request
        params = self.request.query_params
        

        start_date = params.get('start_date')
        end_date = params.get('end_date')

        # If both start_date and end_date are provided, filter the queryset by the date range
        if start_date and end_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                # Assuming your model has a 'created_date' field
                try:
                    queryset = queryset.filter(date__range=[start_date, end_date])
                except:
                    queryset = queryset.filter(created_at__range=[start_date, end_date])
            except ValueError:
                # Handle invalid date format
                pass
        keyword = params.get('keyword')

        if keyword:
            # Filter all character and text fields for similar data
            char_fields = [f.name for f in self.model_name._meta.fields if isinstance(f, models.CharField)]
            text_fields = [f.name for f in self.model_name._meta.fields if isinstance(f, models.TextField)]

            char_queries = [Q(**{f"{field}__icontains": keyword}) for field in char_fields]
            text_queries = [Q(**{f"{field}__icontains": keyword}) for field in text_fields]

            # Combine all queries with OR operator
            combined_queries = char_queries + text_queries
            final_query = combined_queries.pop()
            for query in combined_queries:
                final_query |= query

            queryset = queryset.filter(final_query)

        params = {param: value for param, value in params.items() if param not in ['limit', 'offset','start_date','end_date','keyword','depth','leave_ids','em_id']}
        # Iterate through parameters and filter queryset dynamically
        for param, value in params.items():
            # Check if the parameter corresponds to a field in a related model
            if "__" in param:
                try:
                    queryset = queryset.filter(**{param + "__icontains": value})
                except:
                    queryset = queryset.filter(**{param: value})
            else:
                try:
                    queryset = queryset.filter(**{param + "__icontains": value})
                except:
                    queryset = queryset.filter(**{param: value})

        return queryset.order_by('-id')

    def generate_response(self, success, status_code, message_key, error=None, data=None, page=None):
        model_name = self.model_name.__name__
        message = self.message_templates.get(message_key, "")
        if page is not None:
            data = self.get_paginated_response(data)
        # Convert ErrorDetail objects to strings
        # Ensure error is a dictionary
        # formatted_error = {}
        # if error and isinstance(error, dict):
        #     for key, value in error.items():
        #         formatted_error[key] = [str(error_item) for error_item in value]
        # elif error:
        #     # If error is not None but not a dictionary, handle it as a single error message
        #     formatted_error['_global'] = [str(error)]
        return Response({
            "success": success,
            "status": status_code,
            "message": f"{model_name} {message}",
            "error": error,
            "data": {"results":data}
        })

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
                token = encode_jwt({"data": serializer.data})  # Encode serialized data into JWT token
                return self.generate_response(True, status.HTTP_200_OK, "list_success", data={"token": token})
            else:
                # Pagination requested, apply pagination
                queryset = self.filter_queryset(self.get_queryset())
                page = self.paginate_queryset(queryset)
                if page is not None:
                    serializer = self.get_serializer(page, many=True)
                    token = encode_jwt({"data": serializer.data})  # Encode serialized data into JWT token
                    return self.get_paginated_response({"token": token})
        else:
            return self.generate_response(False, status.HTTP_405_METHOD_NOT_ALLOWED, "list_not_allowed")

    def retrieve(self, request, *args, **kwargs):
        if "retrieve" in self.methods:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            token = encode_jwt({"data": serializer.data})  # Encode serialized data into JWT token
            return self.generate_response(True, status.HTTP_200_OK, "retrieve_success", data={"token": token})
        else:
            return self.generate_response(False, status.HTTP_405_METHOD_NOT_ALLOWED, "retrieve_not_allowed")

    def create(self, request, *args, **kwargs):
        if "create" in self.methods:
            try:
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
                token = encode_jwt({"data": serializer.data})  # Encode serialized data into JWT token
                return self.generate_response(True, status.HTTP_201_CREATED, "create_success", data={"token": token})
            except:
                # print(e)
                return self.generate_response(False, status.HTTP_400_BAD_REQUEST, "create_validation_error", error=serializer.errors)
        else:
            return self.generate_response(False, status.HTTP_405_METHOD_NOT_ALLOWED, "create_not_allowed")

    def update(self, request, *args, **kwargs):
        if "update" in self.methods:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            token = encode_jwt({"data": serializer.data})  # Encode serialized data into JWT token
            return self.generate_response(True, status.HTTP_200_OK, "update_success", data={"token": token})
        else:
            return self.generate_response(False, status.HTTP_405_METHOD_NOT_ALLOWED, "update_not_allowed")

    def partial_update(self, request, *args, **kwargs):
        if "partial_update" in self.methods:
            kwargs['partial'] = True
            return self.update(request, *args, **kwargs)
        else:
            return self.generate_response(False, status.HTTP_405_METHOD_NOT_ALLOWED, "partial_update_not_allowed")

    def destroy(self, request, *args, **kwargs):
        if "destroy" in self.methods:
            instance = self.get_object()
            self.perform_destroy(instance)
            return self.generate_response(True, status.HTTP_204_NO_CONTENT, "destroy_success")
        else:
            return self.generate_response(False, status.HTTP_405_METHOD_NOT_ALLOWED, "destroy_not_allowed")

    @action(detail=True, methods=['post'])
    def soft_delete(self, request, pk=None):
        if "soft_delete" in self.methods:
            item = self.get_object()
            item.is_deleted = True
            item.save()
            return self.generate_response(True, status.HTTP_200_OK, "soft_delete_success")
        else:
            return self.generate_response(False, status.HTTP_405_METHOD_NOT_ALLOWED, "soft_delete_not_allowed")

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        if "change_status" in self.methods:
            item = self.get_object()
            item.status = not item.status
            item.save()
            return self.generate_response(True, status.HTTP_200_OK, "change_status_success")
        else:
            return self.generate_response(False, status.HTTP_405_METHOD_NOT_ALLOWED, "change_status_not_allowed")

    @action(detail=False, methods=['post'])
    def restore_soft_deleted(self, request):
        if "restore_soft_deleted" in self.methods:
            queryset = self.model_name.objects.filter(is_deleted=True)
            queryset.update(is_deleted=False)
            return self.generate_response(True, status.HTTP_200_OK, "restore_soft_deleted_success")
        else:
            return self.generate_response(False, status.HTTP_405_METHOD_NOT_ALLOWED, "restore_soft_deleted_not_allowed")
    def get_serializer_context(self):
        # Get the query parameters from the request
        serializer_context = super().get_serializer_context()
        
        # Check if 'depth' parameter is provided in query parameters
        depth_param = self.request.query_params.get('depth')
        if depth_param is not None:
            # Set the depth parameter in the serializer context
            serializer_context['depth'] = int(depth_param)
        else:
            serializer_context['depth'] = None

        return serializer_context
    # @property
    # def filterset_fields(self):
    #     model = self.model_name
    #     model_fields = model._meta.get_fields()
        
    #     # Generate a list of filter fields excluding fields related to inheritance models
    #     filter_fields = [field.name for field in model_fields if not field.auto_created and not isinstance(field, (ImageField, FileField))]
        
    #     return filter_fields
    # @property
    # def filterset_fields(self):
    #     model = self.model_name
    #     model_fields = model._meta.get_fields()

    #     # Generate a list of filter fields excluding fields related to inheritance models
    #     filter_fields = [field.name for field in model_fields if not field.auto_created and not isinstance(field, (ImageField, FileField))]

    #     # Include CharField and TextField for case-insensitive searching
    #     text_fields = [field.name for field in model_fields if isinstance(field, (CharField, TextField))]

    #     return filter_fields + text_fields
    
        




    ################################# System Settings #########################################
class SystemAssetsViewSet(BaseViews):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated,IsStaff]
    model_name = SoftwareAsset
    methods = ["list", "retrieve", "create", "update", "partial_update", "destroy", "soft_delete", "change_status", "restore_soft_deleted"]
    serializer_class = SoftwareAssetSerializer
class EmailConfigureViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated,IsStaff]
    queryset = DynamicEmailConfiguration.objects.all()
    serializer_class = EmailConfigureSerializer
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            model_name = self.serializer_class.Meta.model.__name__  # Get the model name
            message = "updated successfully"
            success = True
            status_code = status.HTTP_200_OK
            error = None
            data = serializer.data
        except Exception as e:
            model_name = self.serializer_class.Meta.model.__name__  # Get the model name
            message = "update failed"
            success = False
            status_code = status.HTTP_400_BAD_REQUEST
            error = str(e)
            data = None

        return Response({
            "success": success,
            "status": status_code,
            "message": f"{model_name} {message}",
            "error": error,
            "data": {"results": data}
        })
    