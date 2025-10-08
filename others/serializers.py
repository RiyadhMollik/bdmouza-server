from rest_framework import serializers

from others.models import ExtraFeature, Package, PackageItem, Purchases, Tutorial
from globalapp.serializers import GlobalSerializers

class PackageItemSerializer(GlobalSerializers):
    class Meta:
        model = PackageItem
        fields = '__all__'

class PackageSerializer(GlobalSerializers):
    class Meta:
        model = Package
        fields = '__all__'

class TutorialSerializer(GlobalSerializers):
    class Meta:
        model = Tutorial
        fields = '__all__'

class PurchaseSerializer(GlobalSerializers):
    class Meta:
        model = Purchases
        fields = '__all__'
class ExtraFeatureSerializer(GlobalSerializers):
    class Meta:
        model = ExtraFeature
        fields = '__all__'
        