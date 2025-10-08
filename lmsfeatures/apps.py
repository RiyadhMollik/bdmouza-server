from django.apps import AppConfig


class LmsfeaturesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'lmsfeatures'
    def ready(self):
        import lmsfeatures.signals
