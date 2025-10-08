# serializers.py
from rest_framework import serializers

from cms.models import FAQ, Banner, BannerLMS, Blog, Counter, Facilities, Page, SpecialCta, Testimonial
from globalapp.serializers import GlobalSerializers

class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = '__all__'

class BannerLMSSerializer(serializers.ModelSerializer):
    class Meta:
        model = BannerLMS
        fields = '__all__'


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = '__all__'


class TestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimonial
        fields = '__all__'

class BlogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Blog
        fields = '__all__'

class BannerSerializer(GlobalSerializers):
    class Meta:
        model = Banner
        fields = '__all__'

class CounterSerializer(GlobalSerializers):
    class Meta:
        model = Counter
        fields = '__all__'

class FacilitiesSerializer(GlobalSerializers):
    class Meta:
        model = Facilities
        fields = '__all__'

class SpecialCtasSerializer(GlobalSerializers):
    class Meta:
        model = SpecialCta
        fields = '__all__'