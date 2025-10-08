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
        purchases = Purchases.objects.filter(user=user, payment_status='completed')

        all_file_names = []
        for purchase in purchases:
            all_file_names.extend(purchase.file_name or [])

        found_files = []
        for file_name in all_file_names:
            matches = search_file_by_name(file_name)
            for match in matches:
                found_files.append({
                    "name": match.get("name"),
                    "id": match.get("id"),
                    "mimeType": match.get("mimeType"),
                    "parents": match.get("parents")
                })

        return Response({"files": found_files}, status=status.HTTP_200_OK)
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