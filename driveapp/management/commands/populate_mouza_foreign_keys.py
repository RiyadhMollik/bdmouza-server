from django.core.management.base import BaseCommand
from driveapp.models import Mouzamapdata, Division2, District2, SubDistrict


class Command(BaseCommand):
    help = "Populate foreign keys in Mouzamapdata using division, district, and subdistrict names"

    def handle(self, *args, **kwargs):
        updated_count = 0

        for index, mouza in enumerate(Mouzamapdata.objects.all(), start=1):
            updated = False

            # Match Division
            division = Division2.objects.filter(name=mouza.division_name).first()
            if division:
                mouza.division_fk = division
                updated = True

            # Match District
            district = District2.objects.filter(name=mouza.district_name).first()
            if district:
                mouza.district_fk = district
                updated = True

            # Match SubDistrict / Upazila
            subdistrict = SubDistrict.objects.filter(name=mouza.upazila_name).first()
            if subdistrict:
                mouza.subdistrict_fk = subdistrict
                updated = True

            if updated:
                mouza.save(update_fields=["division_fk", "district_fk", "subdistrict_fk"])
                updated_count += 1
                self.stdout.write(f"{index}. ✅ Linked FK for: {mouza}")
            else:
                self.stdout.write(f"{index}. ⚠️ No FK matched for: {mouza}")

        self.stdout.write(self.style.SUCCESS(f"🎉 Foreign keys updated for {updated_count} Mouzamapdata records."))
