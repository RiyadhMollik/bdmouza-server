from django.shortcuts import render

# Create your views here.
# In views.py

import csv
from django.http import HttpResponse
from django.apps import apps
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import permissions
from users.permissions import IsStaff
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table
from openpyxl import Workbook
from django.utils import timezone
import datetime
from reportlab.lib.pagesizes import letter, landscape
class ExportBooks(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated,IsStaff]
    def get(self, request):
        file_type = request.GET.get('file_type', 'csv')
        model_name = request.GET.get('model', 'default_value1')
        app_label = request.GET.get('app_label', 'default_value1')
        model_class = apps.get_model(app_label=app_label, model_name=model_name)

        if file_type == 'excel':
            return self.export_to_excel(model_class, model_name)
        elif file_type == 'pdf':
            return self.export_to_pdf(model_class, model_name)
        else:
            return self.export_to_csv(model_class, model_name)

    def export_to_csv(self, model_class, model_name):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{model_name}.csv"'
        writer = csv.writer(response)

        books = model_class.objects.all()
        fields = [field for field in model_class._meta.get_fields() if not field.is_relation] 
        field_names = [field.name for field in fields]
        writer.writerow(field_names)

        for book in books:
            value = []
            for field in field_names:
                attribute_value = getattr(book, field)
                value.append(attribute_value)
            writer.writerow(value)

        return response

    def export_to_excel(self, model_class, model_name):
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{model_name}.xlsx"'

        books = model_class.objects.all()
        fields = [field.name for field in model_class._meta.get_fields() if not field.is_relation]
        data = []

        for book in books:
            row = []
            for field in fields:
                attribute_value = getattr(book, field)
                if hasattr(attribute_value, 'url'):  # Check if the field is a FileField or ImageField
                    # If it's a FileField or ImageField, get the URL
                    row.append(attribute_value.url)
                elif isinstance(attribute_value, datetime.datetime):
                    # Convert datetime to naive datetime (without timezone)
                    attribute_value = timezone.localtime(attribute_value).replace(tzinfo=None)
                    row.append(attribute_value)
                else:
                    row.append(attribute_value)
            data.append(row)

        wb = Workbook()
        ws = wb.active

        # Write headers
        ws.append(fields)

        # Write data
        for row in data:
            ws.append(row)

        # Save the workbook to the response
        wb.save(response)

        return response
    def export_to_pdf(self, model_class, model_name):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{model_name}.pdf"'

        books = model_class.objects.all()
        fields = [field.name for field in model_class._meta.get_fields() if not field.is_relation]
        data = []

        for book in books:
            row = []
            for field in fields:
                attribute_value = getattr(book, field)
                if isinstance(attribute_value, datetime.datetime):
                    # Convert datetime to the local timezone
                    attribute_value = timezone.localtime(attribute_value)
                row.append(attribute_value)
            data.append(row)

        # Adjust page size to landscape to fit more content horizontally
        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        table_data = [fields] + data
        table = Table(table_data)
        table.setStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)])

        # Reduce font size to fit more content
        table.setStyle([('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 0), (-1, -1), 8)])

        doc.build([table])

        return response
