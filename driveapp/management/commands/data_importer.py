import json
import os
from django.core.management.base import BaseCommand
from driveapp.models import Division2, District2, SubDistrict


class Command(BaseCommand):
    help = "Import divisions, districts, and sub-districts from a JSON file"

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, help='Path to the JSON file', default='data/upazila.json')

    def handle(self, *args, **kwargs):
        file_path = kwargs['file']

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        with open(file_path, encoding='utf-8') as f:
            data = json.load(f).get("data", [])

        division_cache = {}
        district_cache = {}

        # Step 1: Import Divisions and Districts
        for index, item in enumerate(data, start=1):
            # --- Division ---
            division_obj, _ = Division2.objects.update_or_create(
                division_id=item["DIVISION_ID"],
                defaults={
                    "bbs_code": item["DIVISION_BBS_CODE"],
                    "name": item["DIVISION_NAME"],
                    "name_en": item["DIVISION_NAME_EN"],
                }
            )
            division_cache[item["DIVISION_ID"]] = division_obj

            # --- District ---
            district_obj, _ = District2.objects.update_or_create(
                district_id=item["DISTRICT_ID"],
                defaults={
                    "bbs_code": item["DISTRICT_BBS_CODE"],
                    "name": item["DISTRICT_NAME"],
                    "name_en": item["DISTRICT_NAME_EN"],
                    "division_name": division_obj,
                }
            )
            district_cache[item["DISTRICT_ID"]] = district_obj

        # Step 2: Import SubDistricts (with fallback if LAMS_ID is None)
        for index, item in enumerate(data, start=1):
            district_obj = district_cache.get(item["DISTRICT_ID"])
            if not district_obj:
                self.stdout.write(self.style.WARNING(f"{index}. ⚠️ Skipped SubDistrict: District ID {item['DISTRICT_ID']} not found."))
                continue

            lams_id = item.get("LAMS_ID")

            # Try to use LAMS_ID if it's not None
            if lams_id is not None:
                subdistrict_obj, _ = SubDistrict.objects.get_or_create(
                    lams_id=lams_id,
                    defaults={
                        "is_circle": bool(item["IS_CIRCLE"]),
                        "name": item["NAME"],
                        "name_en": item["NAME_EN"],
                        "bbs_code": item["BBS_CODE"],
                        "district_name": district_obj,
                    }
                )
            else:
                # Fallback to composite key
                subdistrict_obj, _ = SubDistrict.objects.get_or_create(
                    name_en=item["NAME_EN"],
                    bbs_code=item["BBS_CODE"],
                    district_name=district_obj,
                    defaults={
                        "is_circle": bool(item["IS_CIRCLE"]),
                        "name": item["NAME"],
                        "lams_id": None,
                    }
                )

            # Always update the rest of the fields
            subdistrict_obj.is_circle = bool(item["IS_CIRCLE"])
            subdistrict_obj.name = item["NAME"]
            subdistrict_obj.name_en = item["NAME_EN"]
            subdistrict_obj.bbs_code = item["BBS_CODE"]
            subdistrict_obj.district_name = district_obj
            subdistrict_obj.lams_id = lams_id
            subdistrict_obj.save()

            self.stdout.write(f"{index}. ✅ Imported SubDistrict: {subdistrict_obj.name_en}")

        self.stdout.write(self.style.SUCCESS("🎉 Import completed successfully."))
