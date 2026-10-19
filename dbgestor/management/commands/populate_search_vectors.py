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
from django.db.models import Count

from dbgestor.models import Lugar, Documento, Persona, Corporacion
from dbgestor.signals import (
    persona_search_vector_expression, documento_search_vector_expression,
    lugar_search_vector_expression, corporacion_search_vector_expression,
)


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
        
        Lugar.objects.update(search_vector=lugar_search_vector_expression())
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Updated {count} Lugar records'))

    def update_documento(self):
        """Update search_vector for all Documento records."""
        self.stdout.write('Updating Documento search vectors...')
        
        count = Documento.objects.count()
        
        Documento.objects.update(
            search_vector=documento_search_vector_expression()
        )
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Updated {count} Documento records'))

    def update_persona(self):
        """Update search_vector for all Persona records.

        Per-row: linked-vocab Spanish aggregates via subqueries, EN vocab text
        computed in Python (double-nested correlation is unresolvable in
        UPDATE). Preloads published EN translations + through links once.
        """
        from django.contrib.contenttypes.models import ContentType
        from dbgestor.models import Translation
        from dbgestor.signals import _persona_vocab_spec
        self.stdout.write('Updating Persona search vectors...')

        en_by_vocab = {}
        links_by_persona = {}
        for vocab_model, through, outer_field, vocab_fk in _persona_vocab_spec():
            ct = ContentType.objects.get_for_model(vocab_model, for_concrete_model=False)
            en_by_vocab[vocab_model] = dict(Translation.objects.filter(
                content_type=ct, status='published').values_list('object_id', 'value'))
            for pid, vpk in through.objects.values_list(outer_field, vocab_fk):
                links_by_persona.setdefault(pid, []).append((vocab_model, vpk))

        def en_text(pid):
            texts = []
            for vm, vpk in links_by_persona.get(pid, []):
                v = en_by_vocab.get(vm, {}).get(vpk)
                if v:
                    texts.append(v)
            return ' '.join(texts)

        pe_ids = set(Persona.objects.filter(
            personaesclavizada__isnull=False).values_list('persona_id', flat=True))
        count = 0
        for pid in Persona.objects.values_list('persona_id', flat=True).iterator():
            Persona.objects.filter(persona_id=pid).update(
                search_vector=persona_search_vector_expression(
                    pid in pe_ids, vocab_en_text=en_text(pid)))
            count += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ Updated {count} Persona records'))

    def update_corporacion(self):
        """Update search_vector for all Corporacion records."""
        self.stdout.write('Updating Corporacion search vectors...')
        
        count = Corporacion.objects.count()
        
        Corporacion.objects.update(search_vector=corporacion_search_vector_expression())
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Updated {count} Corporacion records'))
