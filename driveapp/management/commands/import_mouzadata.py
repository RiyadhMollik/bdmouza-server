import json
import os
from django.core.management.base import BaseCommand
from driveapp.models import Mouzamapdata  # adjust this if your app name is different

class Command(BaseCommand):
    help = 'Import Mouzamapdata from JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file', type=str, help='Path to the JSON file to import'
        )

    def handle(self, *args, **kwargs):
        file_path = kwargs['file'] or 'data/jl_numbers_all.json'

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return

        with open(file_path, encoding='utf-8') as f:
            raw_data = json.load(f)

        # Support for JSON wrapped inside list -> dict -> "data" list
        if isinstance(raw_data, list):
            data_list = []
            for item in raw_data:
                data_list.extend(item.get("data", []))
        elif isinstance(raw_data, dict):
            data_list = raw_data.get("data", [])
        else:
            self.stdout.write(self.style.ERROR('Unrecognized JSON format'))
            return

        created_count = 0
        skipped_count = 0

        for item in data_list:
            try:
                Mouzamapdata.objects.create(
                    mouza_id=item.get("MOUZA_ID"),
                    mouza_name=item.get("MOUZA_NAME"),
                    uuid=item.get("UUID"),
                    jl_number=item.get("JL_NUMBER"),
                    division_name=item.get("DIVISION_NAME"),
                    district_name=item.get("DISTRICT_NAME"),
                    upazila_name=item.get("UPAZILA_NAME"),
                    survey_id=item.get("SURVEY_ID"),
                    mutation_survey_id=item.get("MUTATION_SURVEY_ID"),
                    survey_name=item.get("SURVEY_NAME"),
                    survey_name_en=item.get("SURVEY_NAME_EN"),
                    mutation_survey_name=item.get("MUTATION_SURVEY_NAME"),
                    mutation_survey_name_en=item.get("MUTATION_SURVEY_NAME_EN")
                )
                created_count += 1
            except Exception as e:
                skipped_count += 1
                self.stdout.write(self.style.WARNING(f'Skipped item (ID: {item.get("ID")}) due to error: {e}'))

        self.stdout.write(self.style.SUCCESS(f'✅ Imported {created_count} items.'))
        if skipped_count:
            self.stdout.write(self.style.WARNING(f'⚠️ Skipped {skipped_count} items.'))
