from django.core.management.base import BaseCommand
from django.apps import apps

PUBLISHABLE_MODELS = {
    "documento": "dbgestor.Documento",
    "persona": "dbgestor.Persona",
    "personaesclavizada": "dbgestor.PersonaEsclavizada",
    "personanoesclavizada": "dbgestor.PersonaNoEsclavizada",
    "lugar": "dbgestor.Lugar",
    "corporacion": "dbgestor.Corporacion",
    "historicaldocumento": "dbgestor.HistoricalDocumento",
    "historicalpersona": "dbgestor.HistoricalPersona",
    "historicalpersonaesclavizada": "dbgestor.HistoricalPersonaEsclavizada",
    "historicalpersonanoesclavizada": "dbgestor.HistoricalPersonaNoEsclavizada",
    "historicallugar": "dbgestor.HistoricalLugar",
    "historicalcorporacion": "dbgestor.HistoricalCorporacion",
}


class Command(BaseCommand):
    help = "Publish records for specified models by setting is_published = True"

    def add_arguments(self, parser):
        parser.add_argument(
            '--models',
            nargs='+',
            type=str,
            help='List of model keys to publish (e.g., documento persona)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show how many records would be published without making changes.'
        )

    def handle(self, *args, **options):
        models = options['models']
        dry_run = options['dry_run']

        if not models:
            self.stdout.write(self.style.ERROR("No models specified. Use --models to provide a list."))
            return

        for model_key in models:
            model_path = PUBLISHABLE_MODELS.get(model_key.lower())
            if not model_path:
                self.stdout.write(self.style.WARNING(f"Model key '{model_key}' is not recognized. Skipping."))
                continue

            model = apps.get_model(model_path)
            queryset = model.objects.filter(is_published=False)
            count = queryset.count()

            if dry_run:
                self.stdout.write(self.style.WARNING(f"{model_key}: {count} records would be published (dry run)."))
            else:
                updated = queryset.update(is_published=True)
                self.stdout.write(self.style.SUCCESS(f"{model_key}: {updated} records published."))
