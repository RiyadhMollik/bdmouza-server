# from django_filters import rest_framework as filters
# from django.db.models import CharField, TextField

# class CustomModelFilter(filters.FilterSet):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.set_char_and_text_lookup()

#     def set_char_and_text_lookup(self):
#         for name, field in self.filters.items():
#             if isinstance(field, filters.CharFilter) and self.should_apply_icontains(field):
#                 field.lookup_expr = 'icontains'

#     def should_apply_icontains(self, field):
#         model_field = self._meta.model._meta.get_field(field.field_name)
#         return isinstance(model_field, (CharField, TextField))

#     class Meta:
#         model = YourModel  # Replace YourModel with your actual model name
#         fields = '__all__'  # Or specify the fields you want to filter on
