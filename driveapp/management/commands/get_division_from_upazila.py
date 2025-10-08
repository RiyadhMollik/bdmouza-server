import json
import os
from django.core.management.base import BaseCommand
from driveapp.models import Mouzamapdata


class Command(BaseCommand):
    help = "Update division_name field in Mouzamapdata from upazila.json based on district_name"

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, help='Path to upazila.json', default='data/upazila.json')

    def handle(self, *args, **kwargs):
        file_path = kwargs['file']

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        with open(file_path, encoding='utf-8') as f:
            upazila_data = json.load(f).get("data", [])

        # Build district to division map
        district_to_division = {}
        for item in upazila_data:
            district_name = item.get("DISTRICT_NAME")
            division_name = item.get("DIVISION_NAME")
            if district_name and division_name:
                district_to_division.setdefault(district_name, division_name)

        updated_count = 0

        for index, mouza in enumerate(Mouzamapdata.objects.all(), start=1):
            district = mouza.district_name
            division = district_to_division.get(district, "Not Found")  # Use "Not Found" if not matched

            if mouza.division_name != division:
                mouza.division_name = division
                mouza.save(update_fields=['division_name'])
                updated_count += 1

            if division == "Not Found":
                self.stdout.write(self.style.WARNING(f"{index}. ⚠️ Division not found for district: {district}"))
            else:
                self.stdout.write(f"{index}. ✅ Updated: {district} → {division}")

        self.stdout.write(self.style.SUCCESS(f"✅ Updated {updated_count} objects."))
