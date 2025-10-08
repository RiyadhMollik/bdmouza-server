from django.db import models

from globalapp.models import Common

# Create your models here.
class Division(Common):
    name = models.CharField(max_length=255)
    def __str__(self):
        return f"{self.name}"
class District(Common):
    name = models.CharField(max_length=255)
    division_name = models.ForeignKey(Division,on_delete=models.CASCADE)
    def __str__(self):
        return f"{self.name}"
class Division2(Common):
    bbs_code = models.CharField(max_length=10, unique=True)
    division_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100)

    def __str__(self):
        return self.name_en


class District2(Common):
    bbs_code = models.CharField(max_length=10)
    district_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100)
    division_name = models.ForeignKey(Division2, on_delete=models.CASCADE, related_name='districts')

    def __str__(self):
        return self.name_en


class SubDistrict(Common):  # You may rename this to RevenueCircle if you want
    lams_id = models.IntegerField(null=True)
    is_circle = models.BooleanField()
    name = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100)
    bbs_code = models.CharField(max_length=10)
    district_name = models.ForeignKey(District2, on_delete=models.CASCADE, related_name='sub_districts')
    def __str__(self):
        return self.name_en
class Mouzamapdata(Common):
    
    mouza_id = models.IntegerField()
    mouza_name = models.CharField(max_length=255)
    uuid = models.UUIDField()
    jl_number = models.CharField(max_length=20)
    division_name = models.CharField(max_length=100, null=True, blank=True)
    district_name = models.CharField(max_length=100)
    upazila_name = models.CharField(max_length=100)
    survey_id = models.IntegerField()
    mutation_survey_id = models.IntegerField(null=True, blank=True)
    survey_name = models.CharField(max_length=100)
    survey_name_en = models.CharField(max_length=100)
    mutation_survey_name = models.CharField(max_length=100, null=True, blank=True)
    mutation_survey_name_en = models.CharField(max_length=100, null=True, blank=True)

    
    # ✅ New foreign keys (nullable at first)
    division_fk = models.ForeignKey(Division2, null=True, blank=True, on_delete=models.SET_NULL, related_name='mouzas')
    district_fk = models.ForeignKey(District2, null=True, blank=True, on_delete=models.SET_NULL, related_name='mouzas')
    subdistrict_fk = models.ForeignKey(SubDistrict, null=True, blank=True, on_delete=models.SET_NULL, related_name='mouzas')

    class Meta:
        verbose_name = "Mouza Map Data"
        verbose_name_plural = "Mouza Map Data"

    def __str__(self):
        return f"{self.mouza_name} (JL: {self.jl_number})- {self.district_name}"