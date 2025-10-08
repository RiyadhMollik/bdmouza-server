from django.db import models
from django.db import models
from datetime import datetime
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager,Group,PermissionsMixin
from django.utils import timezone
from globalapp.models import Common
from django.contrib.auth.models import Group, Permission
from phonenumber_field.modelfields import PhoneNumberField
from django.core.validators import RegexValidator
from ckeditor.fields import RichTextField
# Create your models here.


# class Department(models.Model):
#     id = models.AutoField(primary_key=True,default=None)
#     status = models.BooleanField(default=True,null=True,blank=True)
#     created_at= models.DateTimeField(default=datetime.now(),blank=True,null=True)
#     is_deleted = models.BooleanField(default=False,null=True,blank=True)
#     department_name = models.CharField(max_length= 40,default=None)
#     def __str__(self):
#         return f"{self.department_name}"
class Roles(Common):
    name = models.CharField(max_length=15,unique=True)
    menu = models.ManyToManyField(
        Group,
        verbose_name='menu',
        blank=True,
        related_name="user_groups"
    )
    def __str__(self):
        return f"{self.name}"
class MyUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.joined_at = datetime.now()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('is_staff', True)

        return self.create_user(email, password=password, **extra_fields)

class Users(AbstractBaseUser,PermissionsMixin):
    status = models.BooleanField(default=True,null=True,blank=True)
    created_at= models.DateTimeField(default=timezone.now,blank=True,null=True)
    descriptions = RichTextField(null=True,blank=True)
    is_deleted = models.BooleanField(default=False,null=True,blank=True)
    name = models.CharField(max_length=100,default=None,null=True,blank=True)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=15,unique=True,null=True,blank=True)
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',  # You can adjust this regex based on your requirements
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    
    phone_number = models.CharField(
        validators=[phone_regex], max_length=17, null=True, blank=True, unique=True
    )
    whatsapp_number = models.CharField(
        validators=[phone_regex], max_length=17, null=True, blank=True
    )
    profile_picture = models.ImageField(null=True, blank=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    address = models.TextField(max_length=400,default=None,null=True,blank=True)
    # is_company = models.BooleanField(default=False)
    roles = models.ForeignKey(Roles,on_delete=models.CASCADE,related_name="user_roles",null=True,blank=True)
    objects = MyUserManager()

    USERNAME_FIELD = 'email'
    # def get_all_permissions(self, obj=None):
    #     # Define how to retrieve permissions here.
    #     # You can use the roles assigned to the user to determine their permissions.
    #     # For example, you can collect permissions from the associated groups.
    #     permissions = set()
    #     for role in self.roles.all():
    #         permissions.update(role.permissions.all())
    #     print(permissions)
    #     return permissions
    # def has_perm(self, perm, obj=None):
    #     "Does the user have a specific permission?"
    #     # Simplest possible answer: Yes, always
    #     if self.is_admin==True:
    #         return True
    #     # Check if the user directly has the permission
    #     if self.user_permissions.filter(codename=perm).exists():
    #         return True
        
    #     # Check if the user has the permission through roles
        
        
    #     return True

    # def has_module_perms(self, app_label):
    #     "Does the user have permissions to view the app `app_label`?"
    #     # Simplest possible answer: Yes, always
    #     return True
    # def get_all_permissions(self, obj=None):
    #     if self.is_admin:
    #         return set(Permission.objects.all())
        
    #     permissions = set()
    #     if self.roles:
    #         for menu in self.roles.menu.all():
    #             permissions.update(menu.permissions.all())
    #     return permissions
    def get_all_permissions(self, obj=None):
        if self.is_admin:
            permissions = Permission.objects.values_list('content_type__app_label', 'codename')
        else:
            permissions = set()
            if self.roles:
                for menu in self.roles.menu.all():
                    permissions.update(menu.permissions.values_list('content_type__app_label', 'codename'))

        # Convert tuples to "app_label.codename" strings
        return {"{}.{}".format(ct, name) for ct, name in permissions}

    def has_perm(self, perm, obj=None):
        if self.is_admin:
            return True
        if perm in self.get_all_permissions():
            return True
        return False

    def has_module_perms(self, app_label):
        if self.is_admin:
            return True
        return any(perm.split('.')[0] == app_label for perm in self.get_all_permissions())
    def save(self, *args, **kwargs):
        if self.roles is None:
            try:
                self.roles_id = 42659
            except Roles.DoesNotExist:
                pass
        super().save(*args, **kwargs)
    
