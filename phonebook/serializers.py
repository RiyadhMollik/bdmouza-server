from rest_framework import serializers
from .models import Phone
# phone Serializer here
class PhoneSerializer(serializers.ModelSerializer):
    role_name = serializers.SerializerMethodField()
    class Meta:
        model = Phone
        fields = '__all__'
    def get_role_name(self, obj):
        # Get the name of the related contractor
        try:
            if obj.role:
                return obj.role.name
            # return obj.employee_id.first_name + " " + obj.employee_id.last_name
        except:
            pass

        return None