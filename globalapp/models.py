from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from solo.models import SingletonModel
# Create your models here.
class Common(models.Model):
    status = models.BooleanField(default=True,null=True,blank=True)
    created_at= models.DateTimeField(default=timezone.now,blank=True,null=True)
    is_deleted = models.BooleanField(default=False,null=True,blank=True)

class BaseBeneficariesModel(Common):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    nid_number = models.CharField(
        max_length=15,
        unique=True,
        validators=[
            RegexValidator(
                regex='^[0-9]*$',
                message='NID number must contain only numeric values.',
                code='invalid_nid_number'
            )
        ]
    )
    present_address = models.TextField()
    permanent_address = models.TextField()
    profile_picture = models.ImageField(upload_to="profile_pictures/",default="profile_pictures/profile-picture.jpg")
    nid_front = models.ImageField(upload_to="nid/",default="nid/nid_front.jpeg")
    nid_back = models.ImageField(upload_to="nid/",default="nid/nid_back.jpeg")
    def __str__(self):
        return self.name

################################################ APP SETTINGS ########################################################
class SoftwareAsset(Common,SingletonModel):
    title = models.CharField(max_length=50,default="Vitasoft")
    logo = models.ImageField(upload_to='logo/',default=None)
    favicon = models.ImageField(upload_to='logo/',default=None)
    base_color = models.CharField(max_length=10,default="#ffffff")
    primary_color = models.CharField(max_length=10,default="#ff8100")

    
class EmailConfigure(Common,SingletonModel):
    email_password = models.CharField(max_length=50,default=None,null=True,blank=True)
    host = models.CharField(max_length=50,default=None,null=True,blank=True)
    port = models.CharField(max_length=50,default=None,null=True,blank=True)
    user = models.CharField(max_length=50,default=None,null=True,blank=True)
    
    