from django.apps import AppConfig


class DbgestorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dbgestor'

    def ready(self):
        """Import signals when the app is ready."""
        import dbgestor.signals  # noqa
