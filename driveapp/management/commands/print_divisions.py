import unicodedata
from django.core.management.base import BaseCommand
from driveapp.models import Mouzamapdata, Division


class Command(BaseCommand):
    help = "Imports unique division names from Mouzamapdata into the Division model"

    def handle(self, *args, **kwargs):
        raw_divisions = Mouzamapdata.objects.values_list('division_name', flat=True)
        normalized_divisions = set()

        for division in raw_divisions:
            if division and division != "Not Found":
                normalized = unicodedata.normalize("NFC", division.strip())
                normalized_divisions.add(normalized)

        created_count = 0
        for division_name in sorted(normalized_divisions):
            full_name = f"{division_name} বিভাগ"
            obj, created = Division.objects.get_or_create(name=full_name)
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"✅ Created: {full_name}"))
            else:
                self.stdout.write(self.style.WARNING(f"⚠️ Already exists: {full_name}"))

        self.stdout.write(self.style.SUCCESS(f"🎉 Total new divisions added: {created_count}"))
