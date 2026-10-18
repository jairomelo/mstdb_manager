"""Bulk import translation drafts from CSV (idempotent upsert on the key tuple).

CSV columns: object_id, field_name, language_code, value [, status]
For Leccion (--model leccion): object_id, language_code, title, body [, status]

    python manage.py import_translations --model documento --file drafts.csv
    python manage.py import_translations --model leccion --file lecciones.csv --publish
"""

import csv

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError

from dbgestor.models import (
    Leccion, Translation, LeccionTranslation, TRANSLATABLE_MODELS,
)

MODEL_BY_NAME = {name: name for name in TRANSLATABLE_MODELS}


class Command(BaseCommand):
    help = 'Import translation drafts from CSV (upsert on the key tuple)'

    def add_arguments(self, parser):
        parser.add_argument('--model', type=str, required=True,
                            help='Lowercase model name (e.g. documento, tipodocumental, leccion)')
        parser.add_argument('--file', type=str, required=True, help='CSV file path')
        parser.add_argument('--publish', action='store_true',
                            help='Import rows as published instead of draft')

    def handle(self, *args, **options):
        model_name = options['model'].strip().lower()
        default_status = 'published' if options['publish'] else 'draft'
        if model_name == 'leccion':
            created, updated = self._import_lecciones(options['file'], default_status)
        elif model_name in MODEL_BY_NAME:
            created, updated = self._import_generic(model_name, options['file'], default_status)
        else:
            raise CommandError(f'Unknown model "{model_name}". Translatable: leccion + {sorted(MODEL_BY_NAME)}')
        self.stdout.write(self.style.SUCCESS(f'✓ Translations: {created} created, {updated} updated'))

    def _import_generic(self, model_name, path, default_status):
        ct = ContentType.objects.get_by_natural_key('dbgestor', model_name)
        model_class = ct.model_class()
        fields = set(model_class.get_translatable_fields())
        created = updated = 0
        with open(path, newline='', encoding='utf-8') as fh:
            for row in csv.DictReader(fh):
                field = (row.get('field_name') or '').strip()
                lang = (row.get('language_code') or '').strip().lower()
                if not row.get('object_id') or field not in fields or not lang or lang == 'es':
                    raise CommandError(f'Skipping invalid row: {row}')
                if not model_class._default_manager.filter(pk=row['object_id']).exists():
                    raise CommandError(f"{model_name} pk={row['object_id']} does not exist")
                _, was_created = Translation.objects.update_or_create(
                    content_type=ct, object_id=row['object_id'],
                    field_name=field, language_code=lang,
                    defaults={'value': row.get('value', ''),
                              'status': (row.get('status') or default_status).strip() or default_status},
                )
                created += was_created
                updated += not was_created
        return created, updated

    def _import_lecciones(self, path, default_status):
        created = updated = 0
        with open(path, newline='', encoding='utf-8') as fh:
            for row in csv.DictReader(fh):
                lang = (row.get('language_code') or '').strip().lower()
                if not row.get('object_id') or not lang or lang == 'es':
                    raise CommandError(f'Skipping invalid row: {row}')
                if not Leccion.objects.filter(pk=row['object_id']).exists():
                    raise CommandError(f"leccion pk={row['object_id']} does not exist")
                _, was_created = LeccionTranslation.objects.update_or_create(
                    leccion_id=row['object_id'], language_code=lang,
                    defaults={'title': row.get('title', ''), 'body': row.get('body', ''),
                              'status': (row.get('status') or default_status).strip() or default_status},
                )
                created += was_created
                updated += not was_created
        return created, updated
