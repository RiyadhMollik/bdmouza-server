# filters.py
import django_filters
from .models import District2, Division2, Mouzamapdata, SubDistrict


class MouzamapdataFilter(django_filters.FilterSet):
    # Direct fields
    mouza_name = django_filters.CharFilter(lookup_expr='icontains')
    division_name = django_filters.CharFilter(lookup_expr='icontains')
    district_name = django_filters.CharFilter(lookup_expr='icontains')
    upazila_name = django_filters.CharFilter(lookup_expr='icontains')
    survey_name = django_filters.CharFilter(lookup_expr='icontains')  # ✅ Add this line
    survey_name_en = django_filters.CharFilter(lookup_expr='icontains')

    # Related model filters (via FKs)
    division_fk__name = django_filters.CharFilter(field_name='division_fk__name', lookup_expr='icontains')
    district_fk__name = django_filters.CharFilter(field_name='district_fk__name', lookup_expr='icontains')
    subdistrict_fk__name = django_filters.CharFilter(field_name='subdistrict_fk__name', lookup_expr='icontains')

    class Meta:
        model = Mouzamapdata
        fields = [
            'mouza_name', 'jl_number', 'division_name', 'district_name', 'upazila_name','survey_name',
            'division_fk__name', 'district_fk__name', 'subdistrict_fk__name','survey_name_en',
        ]
class Division2Filter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    name_en = django_filters.CharFilter(lookup_expr='icontains')
    bbs_code = django_filters.CharFilter(lookup_expr='exact')
    division_id = django_filters.NumberFilter()

    class Meta:
        model = Division2
        fields = ['name', 'name_en', 'bbs_code', 'division_id']


class District2Filter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    name_en = django_filters.CharFilter(lookup_expr='icontains')
    bbs_code = django_filters.CharFilter(lookup_expr='exact')
    district_id = django_filters.NumberFilter()
    division_name__name = django_filters.CharFilter(field_name='division_name__name', lookup_expr='icontains')

    class Meta:
        model = District2
        fields = ['name', 'name_en', 'bbs_code', 'district_id', 'division_name__name']


class SubDistrictFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    name_en = django_filters.CharFilter(lookup_expr='icontains')
    bbs_code = django_filters.CharFilter(lookup_expr='exact')
    is_circle = django_filters.BooleanFilter()
    lams_id = django_filters.NumberFilter()
    district_name__name = django_filters.CharFilter(field_name='district_name__name', lookup_expr='icontains')

    class Meta:
        model = SubDistrict
        fields = ['name', 'name_en', 'bbs_code', 'is_circle', 'lams_id', 'district_name__name']