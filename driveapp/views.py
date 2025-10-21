import unicodedata
from urllib.parse import unquote

from django.db.models import Q
from django.http import JsonResponse, FileResponse
from django.views import View

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from driveapp.models import District2, Division2, Mouzamapdata, SubDistrict
from driveapp.serializers import (
    District2Serializer,
    Division2Serializer,
    MouzamapdataSerializer,
    SubDistrictSerializer
)
from driveapp.filters import MouzamapdataFilter
from globalapp.views import BaseViews
from globalapp.ed import encode_jwt
from others.models import Purchases
from .drive_utils import (
    convert_file_format,
    download_file_by_id,
    search_file_by_name,
    batch_search_files,
    traverse_drive_path,
    get_drive_service
)

# Optional utility function
def normalize_unicode(text):
    return unicodedata.normalize("NFC", text.strip()) if text else None

class DriveExplorerView(View):
    def get(self, request, *args, **kwargs):
        path = unquote(kwargs.get("path", ""))
        try:
            result = traverse_drive_path(path)
            return JsonResponse(result, safe=False, json_dumps_params={'ensure_ascii': False})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

class DriveFileSearchView(View):
    def get(self, request, *args, **kwargs):
        file_name = request.GET.get("filename")
        if not file_name:
            return JsonResponse({'error': 'Missing "filename" query parameter'}, status=400)

        try:
            file_name = unquote(file_name)
            files = search_file_by_name(file_name)
            return JsonResponse({'files': files}, json_dumps_params={'ensure_ascii': False})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

class DriveFilePreviewByIdView(View):
    def get(self, request, *args, **kwargs):
        file_id = request.GET.get("file_id")
        if not file_id:
            return JsonResponse({'error': 'Missing "file_id" query parameter'}, status=400)

        try:
            # 🔧 Always compress
            stream, mime_type, filename = download_file_by_id(file_id, compress=True)
            return FileResponse(stream, content_type=mime_type, filename=filename)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

class MouzamapdataViewSet(BaseViews):
    model_name = Mouzamapdata
    methods = ["list", "retrieve"]
    queryset = Mouzamapdata.objects.all()
    serializer_class = MouzamapdataSerializer

    @action(detail=False, methods=["get"], url_path="get-survey-names")
    def get_survey_names(self, request):
        division_name = normalize_unicode(request.GET.get("division_fk__name"))
        district_name = normalize_unicode(request.GET.get("district_fk__name"))
        subdistrict_name = normalize_unicode(request.GET.get("subdistrict_fk__name"))

        filters = Q()
        if division_name:
            filters &= Q(division_fk__name__icontains=division_name)
        if district_name:
            filters &= Q(district_fk__name__icontains=district_name)
        if subdistrict_name:
            filters &= Q(subdistrict_fk__name__icontains=subdistrict_name)

        queryset = self.get_queryset().filter(filters)

        survey_name_en_list = (
            queryset
            .values_list("survey_name_en", flat=True)
            .distinct()
            .order_by("survey_name_en")
        )

        token = encode_jwt({"survey_name_en_list": list(survey_name_en_list)})
        return self.generate_response(
            True,
            status.HTTP_200_OK,
            "success",
            data={"token": token}
        )

class Division2ViewSet(BaseViews):
    model_name = Division2
    methods = ["list", "retrieve"]
    queryset = Division2.objects.all()
    serializer_class = Division2Serializer

class District2ViewSet(BaseViews):
    model_name = District2
    methods = ["list", "retrieve"]
    queryset = District2.objects.all()
    serializer_class = District2Serializer

class SubDistrictViewSet(BaseViews):
    model_name = SubDistrict
    methods = ["list", "retrieve"]
    queryset = SubDistrict.objects.all()
    serializer_class = SubDistrictSerializer

class UserPurchasedFilesView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Add pagination parameters
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 5))  # Limit to 5 files per request
        offset = (page - 1) * page_size
        
        try:
            purchases = Purchases.objects.filter(user=user, payment_status='completed')
            
            # Collect all file names
            all_file_names = []
            for purchase in purchases:
                if purchase.file_name:
                    all_file_names.extend(purchase.file_name)
            
            # Remove duplicates and apply pagination
            unique_file_names = list(set(all_file_names))
            total_files = len(unique_file_names)
            paginated_file_names = unique_file_names[offset:offset + page_size]
            
            found_files = []
            failed_files = []
            
            # Use batch search for better performance
            try:
                batch_result = batch_search_files(
                    paginated_file_names, 
                    max_workers=3  # Limit concurrent requests
                )
                
                # Process successful results
                for file_name, matches in batch_result['results'].items():
                    if matches:
                        for match in matches[:2]:  # Limit to first 2 matches per file
                            found_files.append({
                                "name": match.get("name"),
                                "id": match.get("id"),
                                "mimeType": match.get("mimeType"),
                                "parents": match.get("parents"),
                                "original_search": file_name
                            })
                    else:
                        failed_files.append({
                            "name": file_name,
                            "error": "File not found in Google Drive"
                        })
                
                # Process errors
                for failed_file in batch_result['failed_files']:
                    failed_files.append({
                        "name": failed_file['file_name'],
                        "error": failed_file['error']
                    })
                    
            except Exception as e:
                # Fallback to individual searches if batch fails
                for file_name in paginated_file_names:
                    try:
                        matches = search_file_by_name(file_name)
                        if matches:
                            match = matches[0]  # Take only first match
                            found_files.append({
                                "name": match.get("name"),
                                "id": match.get("id"),
                                "mimeType": match.get("mimeType"),
                                "parents": match.get("parents"),
                                "original_search": file_name
                            })
                        else:
                            failed_files.append({
                                "name": file_name,
                                "error": "File not found in Google Drive"
                            })
                    except Exception as individual_error:
                        failed_files.append({
                            "name": file_name,
                            "error": str(individual_error)
                        })
                        continue
            
            # Calculate pagination info
            has_next = offset + page_size < total_files
            has_previous = page > 1
            
            response_data = {
                "files": found_files,
                "failed_files": failed_files if failed_files else None,
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_files": total_files,
                    "total_pages": (total_files + page_size - 1) // page_size,
                    "has_next": has_next,
                    "has_previous": has_previous,
                    "files_in_current_page": len(found_files)
                }
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "error": "Failed to fetch purchased files",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserPurchasedFilesBatchView(APIView):
    """
    Optimized version for fetching all files with better performance
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        try:
            purchases = Purchases.objects.filter(user=user, payment_status='completed')
            
            # Collect all file names efficiently
            all_file_names = set()  # Use set to avoid duplicates
            for purchase in purchases:
                if purchase.file_name:
                    all_file_names.update(purchase.file_name)
            
            total_files = len(all_file_names)
            
            # If too many files, suggest using paginated endpoint
            if total_files > 50:
                return Response({
                    "message": "Too many files to fetch at once. Please use paginated endpoint.",
                    "total_files": total_files,
                    "suggestion": "Use /api/drive/user-purchased-files/ with page and page_size parameters",
                    "recommended_page_size": 20
                }, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
            
            found_files = []
            failed_files = []
            
            # Use batch search for all files
            try:
                batch_result = batch_search_files(
                    list(all_file_names), 
                    max_workers=4  # Slightly higher for batch
                )
                
                # Process successful results
                for file_name, matches in batch_result['results'].items():
                    if matches:
                        # Take only the first match to avoid duplicates
                        match = matches[0]
                        found_files.append({
                            "name": match.get("name"),
                            "id": match.get("id"),
                            "mimeType": match.get("mimeType"),
                            "parents": match.get("parents"),
                            "original_search": file_name
                        })
                    else:
                        failed_files.append({
                            "name": file_name,
                            "error": "File not found in Google Drive"
                        })
                
                # Process errors
                for failed_file in batch_result['failed_files']:
                    failed_files.append({
                        "name": failed_file['file_name'],
                        "error": failed_file['error']
                    })
                    
            except Exception as batch_error:
                # Fallback to individual processing if batch completely fails
                return Response({
                    "error": "Batch processing failed, too many files to process",
                    "details": str(batch_error),
                    "suggestion": "Use the paginated endpoint: /api/drive/user-purchased-files/"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({
                "files": found_files,
                "failed_files": failed_files if failed_files else None,
                "summary": {
                    "total_searched": total_files,
                    "found": len(found_files),
                    "failed": len(failed_files),
                    "success_rate": f"{(len(found_files) / total_files * 100):.1f}%" if total_files > 0 else "0%"
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "error": "Failed to fetch purchased files",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DriveFileConvertView(View):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        file_id = request.GET.get("file_id")
        target_format = request.GET.get("format", "").lower()

        if not file_id or target_format not in ["pdf", "jpg"]:
            return JsonResponse({'error': 'Invalid file_id or format'}, status=400)

        try:
            stream, mime_type, filename = download_file_by_id(file_id, compress=False)
            # Convert only if not already in target format
            if (target_format == "pdf" and mime_type != "application/pdf") or \
               (target_format == "jpg" and mime_type not in ["image/jpeg", "image/png"]):
                stream, mime_type, filename = convert_file_format(stream, mime_type, target_format)

            return FileResponse(stream, content_type=mime_type, filename=filename)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)