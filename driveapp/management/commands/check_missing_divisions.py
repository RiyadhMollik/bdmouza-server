import json
from django.core.management.base import BaseCommand
from driveapp.models import Mouzamapdata

class Command(BaseCommand):
    help = "Update division_name for Mouzamapdata using hardcoded corrections (without 'বিভাগ') and fallback to upazila.json"

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, help='Path to upazila.json', default='data/upazila.json')

    def handle(self, *args, **kwargs):
        upazila_file_path = kwargs['file']

        # Hardcoded corrections: only division name (without 'বিভাগ')
        correction_map = {
            "কুড়িগ্রাম": "রংপুর",
            "কুমিল্লা": "চট্টগ্রাম",
            "কুষ্টিয়া": "খুলনা",
            "খুলনা": "খুলনা",
            "গাজীপুর": "ঢাকা",
            "চট্টগ্রাম": "চট্টগ্রাম",
            "চুয়াডাঙ্গা": "খুলনা",
            "চুয়াডাঙ্গা সদর": "খুলনা",
            "জামালপুর": "ময়মনসিংহ",
            "জয়পুরহাট": "খুলনা",
            "জয়পুরহাট সদর": "খুলনা",
            "ঝিনাইদহ": "খুলনা",
            "টাঙ্গাইল": "ঢাকা",
            "টাঙ্গাইল সদর": "ঢাকা",
            "ঠাকুরগাঁও": "ঢাকা",
            "ঢাকা": "ঢাকা",
            "ত্রিপুরা": "চট্টগ্রাম",
            "দিনাজপুর": "রংপুর",
            "নওগাঁ": "রাজশাহী",
            "নওগাঁ সদর": "রাজশাহী",
            "নড়াইল": "খুলনা",
            "নলডাঙ্গা": "রাজশাহী",
            "নারায়ণগঞ্জ": "ঢাকা",
            "নেত্রকোনা": "ময়মনসিংহ",
            "নোয়াখালী": "চট্টগ্রাম",
            "পঞ্চগড়": "রংপুর",
            "পটুয়াখালী": "বরিশাল",
            "পশ্চিম পিপুলজুড়ি": "Not Found",
            "পাংশা": "ঢাকা",
            "পাবনা": "রাজশাহী",
            "ফরিদপুর": "ঢাকা",
            "ফেনী": "চট্টগ্রাম",
            "ফেনী সদর": "চট্টগ্রাম",
            "বগুড়া": "রাজশাহী",
            "বরগুনা": "বরিশাল",
            "বাকেরগঞ্জ": "বরিশাল",
            "বাগেরহাট": "খুলনা",
            "বালিয়াকান্দি": "ঢাকা",
            "ব্রাহ্মণবাড়িয়া": "চট্টগ্রাম",
            "মান্দা": "রাজশাহী",
            "মুন্সীগঞ্জ": "ঢাকা",
            "মেহেন্দিগঞ্জ": "বরিশাল",
            "মেহেরপুর": "খুলনা",
            "মৌলভীবাজার": "সিলেট",
            "ময়মনসিংহ": "ময়মনসিংহ",
            "যশোর": "খুলনা",
            "রংপুর": "রংপুর",
            "রাজবাড়ী": "ঢাকা",
            "রাজশাহী": "রাজশাহী",
            "রৌমারী": "রংপুর",
            "লোহাগড়া": "চট্টগ্রাম",
            "সাতক্ষীরা": "খুলনা",
            "সিরাজগঞ্জ": "রাজশাহী",
            "সিলেট": "সিলেট",
            "সুনামগঞ্জ": "সিলেট",
            "স্বরুপকাঠী": "বরিশাল",
            "হবিগঞ্জ": "সিলেট"
        }

        # Load upazila.json for fallback (stripping 'বিভাগ')
        district_to_division = {}
        try:
            with open(upazila_file_path, encoding='utf-8') as f:
                upazila_data = json.load(f).get("data", [])
            for item in upazila_data:
                district = item.get("DISTRICT_NAME", "").strip()
                division = item.get("DIVISION_NAME", "").replace(" বিভাগ", "").strip()
                if district and division:
                    district_to_division[district] = division
        except FileNotFoundError:
            self.stdout.write(self.style.WARNING(f"⚠️ upazila.json not found at {upazila_file_path}"))

        updated_count = 0
        not_found_count = 0

        for i, mouza in enumerate(Mouzamapdata.objects.all(), start=1):
            district = mouza.district_name.strip()

            # Use correction if available
            new_division = correction_map.get(district)

            # Fallback to upazila.json
            if not new_division:
                new_division = district_to_division.get(district, "Not Found")

            if mouza.division_name != new_division:
                mouza.division_name = new_division
                mouza.save(update_fields=['division_name'])
                updated_count += 1

            if new_division == "Not Found":
                not_found_count += 1
                self.stdout.write(self.style.WARNING(f"{i}. ⚠️ Not Found: {district}"))
            else:
                self.stdout.write(f"{i}. ✅ Updated: {district} → {new_division}")

        self.stdout.write(self.style.SUCCESS(f"\n✅ Total updated: {updated_count}"))
        self.stdout.write(self.style.WARNING(f"⚠️ Total 'Not Found': {not_found_count}"))
