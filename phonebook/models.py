from django.db import models
from django.core.validators import RegexValidator
from globalapp.models import BaseBeneficariesModel, Common
from users.models import Roles

# Create your models here.
class Phone(Common):
    contact_name = models.CharField(max_length=100)
    relation = models.CharField(max_length=100,blank=True,null=True)
    phone_number = models.CharField(
        max_length=15,  # Adjust the max_length as per your phone number format
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',  # Adjust the regex according to your desired phone number format
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            ),
        ],
    
    )
    role = models.ForeignKey(Roles,blank=True, null=True,on_delete=models.CASCADE,related_name="phone_roles")
    #benificaries model come here
    ben_id = models.ForeignKey(BaseBeneficariesModel,blank=True,null=True,on_delete=models.CASCADE)
    

    def __str__(self):
        return self.contact_name
