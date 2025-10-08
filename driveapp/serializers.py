from rest_framework import serializers


from driveapp.models import District2, Division2, Mouzamapdata, SubDistrict
from globalapp.serializers import GlobalSerializers

# class MouzamapdataSerializer(GlobalSerializers):
#     class Meta:
#         model = Mouzamapdata
#         fields = '__all__'

class Division2Serializer(GlobalSerializers):
    class Meta:
        model = Division2
        fields = ['id', 'name', 'name_en', 'bbs_code', 'division_id']


class District2Serializer(GlobalSerializers):
    division_name = Division2Serializer()

    class Meta:
        model = District2
        fields = ['id', 'name', 'name_en', 'bbs_code', 'district_id', 'division_name']


class SubDistrictSerializer(GlobalSerializers):
    district_name = District2Serializer()

    class Meta:
        model = SubDistrict
        fields = ['id', 'name', 'name_en', 'bbs_code', 'lams_id', 'is_circle', 'district_name']


class MouzamapdataSerializer(GlobalSerializers):
    division_fk = Division2Serializer()
    district_fk = District2Serializer()
    subdistrict_fk = SubDistrictSerializer()

    class Meta:
        model = Mouzamapdata
        fields = '__all__'