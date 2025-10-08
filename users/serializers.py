from rest_framework import serializers
from django.contrib.auth.models import Group, Permission
from users.models import Roles, Users

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from phonenumber_field.serializerfields import PhoneNumberField
#custom token

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        username_or_email = attrs.get('email')
        password = attrs.get('password')

        if username_or_email is None or password is None:
            raise ValidationError('Both username/email and password must be provided.')

        user = get_user_model().objects.filter(username=username_or_email).first()
        attrs['email']=user
        if user is None:
            user = get_user_model().objects.filter(email=username_or_email).first()
            attrs['email']=user
        if user is None or not user.check_password(password):
            raise ValidationError('No active account found with the given credentials.')
        
        return super().validate(attrs)

class AllUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = Users
        fields = '__all__'
        depth =3
class RolesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Roles
        fields = '__all__'
        # depth =3
class GropuSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = '__all__'
class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = '__all__' 

class UserSerializer(serializers.ModelSerializer):
    # profile_picture = serializers.SerializerMethodField()
    
    class Meta:
        model = Users
        fields = '__all__'
        extra_kwargs = {'password': {'write_only': True}}  # Ensure password field is write-only

    def create(self, validated_data):
        # print("from user serialize: ",data)
        password = validated_data.pop('password')
        user = Users.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        try:
            send_registration_email(user.email, password)
        except:
            pass
        return user
    def update(self, instance, validated_data):
        # print("email checker: ",updated_instance.email,updated_instance.password)
        if 'password' in validated_data:
            password = validated_data.pop('password')
            instance.set_password(password)
        updated_instance = super().update(instance, validated_data)
        try:
            print(updated_instance.email,updated_instance.password)
            send_registration_email(updated_instance.email,updated_instance.password)
        except:
            pass
        return updated_instance
    def get_profile_picture(self, obj):
        # Return full URL for profile_picture
        request = self.context.get('request')
        if obj.profile_picture and request is not None:
            return request.build_absolute_uri(obj.profile_picture.url)
        return None
    
def send_registration_email(email, password):
    subject = 'Welcome to Our Platform!'
    context = {'email': email, 'password': password}
    html_content = render_to_string('users/registration_email.html', context)
    text_content = strip_tags(html_content)
    from_email = 'your@example.com'  # Update with your email address
    recipient_list = [email]

    msg = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
    msg.attach_alternative(html_content, "text/html")
    msg.send()
