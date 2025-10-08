from rest_framework import serializers

from des.models import DynamicEmailConfiguration
from globalapp.models import SoftwareAsset
class GlobalSerializers(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        # Initialize the serializer
        super().__init__(*args, **kwargs)
        
        # Check if 'depth' parameter is provided in context
        if 'context' in kwargs and 'depth' in kwargs['context']:
            # Apply the depth parameter to the serializer
            self.Meta.depth = kwargs['context']['depth']

#System Settings API
class SoftwareAssetSerializer(GlobalSerializers):
    class Meta:
        model = SoftwareAsset
        fields = '__all__'
class EmailConfigureSerializer(GlobalSerializers):
    class Meta:
        model = DynamicEmailConfiguration
        fields = '__all__'