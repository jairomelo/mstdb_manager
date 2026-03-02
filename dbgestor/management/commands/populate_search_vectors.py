"""
Management command to populate search_vector fields for existing records.

Run after migrating the search fields:
    python manage.py populate_search_vectors

This command updates the search_vector field for all existing records in:
- Lugar
- Documento
- Persona (and subclasses)
- Corporacion
"""

from django.core.management.base import BaseCommand
from django.contrib.postgres.search import SearchVector
from django.db.models import Count

from dbgestor.models import Lugar, Documento, Persona, Corporacion


class Command(BaseCommand):
    help = 'Populate search_vector fields for existing records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            choices=['lugar', 'documento', 'persona', 'corporacion', 'all'],
            default='all',
            help='Which model to update (default: all)',
        )

    def handle(self, *args, **options):
        model_name = options['model']

        if model_name in ['lugar', 'all']:
            self.update_lugar()
        
        if model_name in ['documento', 'all']:
            self.update_documento()
        
        if model_name in ['persona', 'all']:
            self.update_persona()
        
        if model_name in ['corporacion', 'all']:
            self.update_corporacion()

        self.stdout.write(self.style.SUCCESS('✓ Search vectors updated successfully'))

    def update_lugar(self):
        """Update search_vector for all Lugar records."""
        self.stdout.write('Updating Lugar search vectors...')
        
        count = Lugar.objects.count()
        
        Lugar.objects.update(
            search_vector=(
                SearchVector('nombre_lugar', weight='A', config='spanish') +
                SearchVector('otros_nombres', weight='B', config='spanish') +
                SearchVector('tipo', weight='C', config='spanish')
            )
        )
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Updated {count} Lugar records'))

    def update_documento(self):
        """Update search_vector for all Documento records."""
        self.stdout.write('Updating Documento search vectors...')
        
        count = Documento.objects.count()
        
        Documento.objects.update(
            search_vector=(
                SearchVector('titulo', weight='A', config='spanish') +
                SearchVector('descripcion', weight='B', config='spanish') +
                SearchVector('notas', weight='C', config='spanish') +
                SearchVector('sigla_documento', weight='D', config='spanish')
            )
        )
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Updated {count} Documento records'))

    def update_persona(self):
        """Update search_vector for all Persona records."""
        self.stdout.write('Updating Persona search vectors...')
        
        count = Persona.objects.count()
        
        Persona.objects.update(
            search_vector=(
                SearchVector('nombre_normalizado', weight='A', config='spanish') +
                SearchVector('nombres', weight='A', config='spanish') +
                SearchVector('apellidos', weight='A', config='spanish') +
                SearchVector('notas', weight='C', config='spanish') +
                SearchVector('ocupacion_categoria', weight='D', config='spanish')
            )
        )
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Updated {count} Persona records'))

    def update_corporacion(self):
        """Update search_vector for all Corporacion records."""
        self.stdout.write('Updating Corporacion search vectors...')
        
        count = Corporacion.objects.count()
        
        Corporacion.objects.update(
            search_vector=(
                SearchVector('nombre_institucion', weight='A', config='spanish') +
                SearchVector('nombres_alternativos', weight='B', config='spanish') +
                SearchVector('notas', weight='C', config='spanish')
            )
        )
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Updated {count} Corporacion records'))
