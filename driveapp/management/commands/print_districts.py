# import json
# import unicodedata
# import google.generativeai as genai

# from django.core.management.base import BaseCommand
# from driveapp.models import Mouzamapdata


# class Command(BaseCommand):
#     help = "Checks and corrects unique district names in Mouzamapdata using Gemini, ensuring unique valid output"

#     def add_arguments(self, parser):
#         parser.add_argument('--api_key', type=str, required=True, help='Your Gemini API key')
#         parser.add_argument('--save', action='store_true', help='Save results to corrected_districts.json')

#     def handle(self, *args, **kwargs):
#         api_key = kwargs['api_key']
#         genai.configure(api_key=api_key)
#         model = genai.GenerativeModel("models/gemini-1.5-pro-latest")

#         # Step 1: Get unique normalized district names from DB
#         raw_districts = Mouzamapdata.objects.values_list('district_name', flat=True)
#         unique_districts = set()
#         for d in raw_districts:
#             if d:
#                 normalized = unicodedata.normalize("NFC", d.strip())
#                 unique_districts.add(normalized)

#         corrected_map = {}  # map original → corrected
#         suggested_names = set()  # to track unique suggested names

#         self.stdout.write(f"🔍 Checking {len(unique_districts)} unique districts with Gemini...\n")

#         for count, district in enumerate(sorted(unique_districts), start=1):
#             try:
#                 prompt = (
#                     f"'{district}' কি বাংলাদেশের ৬৪টি জেলার মধ্যে একটি সঠিক নাম? "
#                     f"যদি না হয়, অনুগ্রহ করে শুধুমাত্র সঠিক জেলার নামটি লিখুন। "
#                     f"উদাহরণস্বরূপ: ঢাকা, কুমিল্লা, রাজশাহী ইত্যাদি। "
#                     f"শুধুমাত্র নাম দিন, অন্য কিছু নয়।"
#                 )
#                 response = model.generate_content(prompt)
#                 suggestion = response.text.strip()

#                 # Avoid duplicates in output
#                 if suggestion not in suggested_names:
#                     suggested_names.add(suggestion)
#                     status = "✅"
#                 else:
#                     status = "🔁 (Duplicate suggestion, skipped printing)"

#                 corrected_map[district] = suggestion
#                 self.stdout.write(f"{count}. {district} → {suggestion} {status}")

#             except Exception as e:
#                 self.stderr.write(self.style.ERROR(f"{count}. ❌ Error with '{district}': {e}"))

#         # Save output if requested
#         if kwargs.get("save"):
#             with open("corrected_districts.json", "w", encoding="utf-8") as f:
#                 json.dump(corrected_map, f, ensure_ascii=False, indent=2)
#             self.stdout.write(self.style.SUCCESS("✅ Saved corrected districts to corrected_districts.json"))

#         self.stdout.write(self.style.SUCCESS(f"\n✅ Finished checking. Total unique suggestions: {len(suggested_names)}"))
import json
import unicodedata
import google.generativeai as genai

from django.core.management.base import BaseCommand
from driveapp.models import Mouzamapdata, District, Division

# Correct district → division mapping
DISTRICT_TO_DIVISION = {
    "ঢাকা": "ঢাকা",
    "ফরিদপুর": "ঢাকা",
    "গাজীপুর": "ঢাকা",
    "নারায়ণগঞ্জ": "ঢাকা",
    "মুন্সীগঞ্জ": "ঢাকা",
    "রাজবাড়ী": "ঢাকা",
    "টাঙ্গাইল": "ঢাকা",
    "কিশোরগঞ্জ": "ঢাকা",
    "মানিকগঞ্জ": "ঢাকা",
    "মাদারীপুর": "ঢাকা",
    "শরীয়তপুর": "ঢাকা",
    "নরসিংদী": "ঢাকা",

    "চট্টগ্রাম": "চট্টগ্রাম",
    "কুমিল্লা": "চট্টগ্রাম",
    "নোয়াখালী": "চট্টগ্রাম",
    "ফেনী": "চট্টগ্রাম",
    "লক্ষ্মীপুর": "চট্টগ্রাম",
    "খাগড়াছড়ি": "চট্টগ্রাম",
    "বান্দরবান": "চট্টগ্রাম",
    "রাঙ্গামাটি": "চট্টগ্রাম",
    "ব্রাহ্মণবাড়িয়া": "চট্টগ্রাম",
    "চাঁদপুর": "চট্টগ্রাম",
    "কক্সবাজার": "চট্টগ্রাম",

    "রাজশাহী": "রাজশাহী",
    "নওগাঁ": "রাজশাহী",
    "নাটোর": "রাজশাহী",
    "চাঁপাইনবাবগঞ্জ": "রাজশাহী",
    "বগুড়া": "রাজশাহী",
    "সিরাজগঞ্জ": "রাজশাহী",
    "জয়পুরহাট": "রাজশাহী",
    "পাবনা": "রাজশাহী",

    "খুলনা": "খুলনা",
    "যশোর": "খুলনা",
    "ঝিনাইদহ": "খুলনা",
    "মাগুরা": "খুলনা",
    "নড়াইল": "খুলনা",
    "বাগেরহাট": "খুলনা",
    "চুয়াডাঙ্গা": "খুলনা",
    "মেহেরপুর": "খুলনা",
    "সাতক্ষীরা": "খুলনা",

    "বরিশাল": "বরিশাল",
    "পটুয়াখালী": "বরিশাল",
    "পিরোজপুর": "বরিশাল",
    "বরগুনা": "বরিশাল",
    "ঝালকাঠি": "বরিশাল",
    "ভোলা": "বরিশাল",

    "সিলেট": "সিলেট",
    "হবিগঞ্জ": "সিলেট",
    "মৌলভীবাজার": "সিলেট",
    "সুনামগঞ্জ": "সিলেট",

    "রংপুর": "রংপুর",
    "দিনাজপুর": "রংপুর",
    "নীলফামারী": "রংপুর",
    "ঠাকুরগাঁও": "রংপুর",
    "কুড়িগ্রাম": "রংপুর",
    "লালমনিরহাট": "রংপুর",
    "পঞ্চগড়": "রংপুর",
    "গাইবান্ধা": "রংপুর",

    "ময়মনসিংহ": "ময়মনসিংহ",
    "জামালপুর": "ময়মনসিংহ",
    "নেত্রকোনা": "ময়মনসিংহ",
    "শেরপুর": "ময়মনসিংহ",
}


class Command(BaseCommand):
    help = "Uses Gemini to correct district names, and inserts them into District & Division models"

    def add_arguments(self, parser):
        parser.add_argument('--api_key', type=str, required=True, help='Your Gemini API key')

    def handle(self, *args, **kwargs):
        api_key = kwargs['api_key']
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("models/gemini-1.5-pro-latest")

        # Step 1: Get unique district names from database
        raw_districts = Mouzamapdata.objects.values_list('district_name', flat=True)
        unique_districts = set()
        for d in raw_districts:
            if d:
                normalized = unicodedata.normalize("NFC", d.strip())
                unique_districts.add(normalized)

        self.stdout.write(f"🔍 Checking {len(unique_districts)} unique districts with Gemini...\n")

        inserted = 0
        already = 0

        for count, district in enumerate(sorted(unique_districts), start=1):
            try:
                prompt = (
                    f"'{district}' কি বাংলাদেশের ৬৪ জেলার মধ্যে একটি? যদি না হয়, শুধুমাত্র সঠিক জেলার নামটি লিখুন। "
                    f"কোন ব্যাখ্যার প্রয়োজন নেই, শুধু সঠিক জেলার নাম দিন।"
                )
                response = model.generate_content(prompt)
                suggestion = response.text.strip()

                if suggestion not in DISTRICT_TO_DIVISION:
                    self.stdout.write(f"{count}. ⚠️ Skipped: '{district}' → '{suggestion}' (Unknown)")
                    continue

                division_clean = DISTRICT_TO_DIVISION[suggestion]
                division_name = f"{division_clean} বিভাগ"

                # Create or get division
                division_obj, _ = Division.objects.get_or_create(name=division_name)

                # Create or get district
                district_obj, created = District.objects.get_or_create(name=suggestion, division_name=division_obj)
                if created:
                    inserted += 1
                    self.stdout.write(f"{count}. ✅ Inserted: {suggestion} → {division_name}")
                else:
                    already += 1
                    self.stdout.write(f"{count}. 🔁 Exists: {suggestion}")

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"{count}. ❌ Error with '{district}': {e}"))

        self.stdout.write(self.style.SUCCESS(f"\n✅ Inserted {inserted} new districts. Already existed: {already}"))
