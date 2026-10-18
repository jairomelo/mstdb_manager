"""Phase 1 tests: translation rows, fallback resolution, uniqueness, CSV upsert."""

import csv
import tempfile

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase

from dbgestor.models import (
    Archivo, ConductaTerm, Documento, Leccion, LeccionTranslation,
    Lugar, PersonaEsclavizada, TipoDocumental, Translation,
    get_translation, resolve_translated_fields,
)


class TranslationModelTests(TestCase):
    def setUp(self):
        archivo = Archivo.objects.create(nombre='Archivo Test T')
        tipo = TipoDocumental.objects.create(tipo_documental='Carta')
        self.doc = Documento.objects.create(
            archivo=archivo, fondo='F', unidad_documental_compuesta='U',
            folio_inicial='1', tipo_documento=tipo,
            titulo='Venta de una casa', descripcion='Escritura',
        )
        self.ct = ContentType.objects.get_for_model(Documento)

    def test_unique_cell_constraint(self):
        Translation.objects.create(
            content_type=self.ct, object_id=self.doc.pk, field_name='titulo',
            language_code='en', value='Sale of a house')
        with self.assertRaises(Exception):
            Translation.objects.create(
                content_type=self.ct, object_id=self.doc.pk, field_name='titulo',
                language_code='en', value='Duplicate')

    def test_untranslatable_field_rejected(self):
        row = Translation(
            content_type=self.ct, object_id=self.doc.pk, field_name='fondo',
            language_code='en', value='Fund')
        with self.assertRaises(ValidationError):
            row.full_clean()

    def test_spanish_language_code_rejected(self):
        row = Translation(
            content_type=self.ct, object_id=self.doc.pk, field_name='titulo',
            language_code='es', value='Venta')
        with self.assertRaises(ValidationError):
            row.full_clean()

    def test_untranslatable_model_rejected(self):
        ct = ContentType.objects.get_for_model(Archivo)
        row = Translation(
            content_type=ct, object_id=1, field_name='nombre',
            language_code='en', value='Archive')
        with self.assertRaises(ValidationError):
            row.full_clean()

    def test_fallback_to_spanish_when_no_published_row(self):
        self.assertEqual(get_translation(self.doc, 'titulo', 'en'), 'Venta de una casa')
        self.assertEqual(get_translation(self.doc, 'titulo', 'xx'), 'Venta de una casa')
        self.assertEqual(get_translation(self.doc, 'titulo', 'es'), 'Venta de una casa')

    def test_draft_not_visible_until_published(self):
        Translation.objects.create(
            content_type=self.ct, object_id=self.doc.pk, field_name='titulo',
            language_code='en', value='Sale of a house', status='draft')
        self.assertEqual(get_translation(self.doc, 'titulo', 'en'), 'Venta de una casa')
        row = Translation.objects.get(content_type=self.ct, object_id=self.doc.pk)
        row.status = 'published'
        row.save()
        self.assertEqual(get_translation(self.doc, 'titulo', 'en'), 'Sale of a house')

    def test_resolve_translated_fields(self):
        Translation.objects.create(
            content_type=self.ct, object_id=self.doc.pk, field_name='titulo',
            language_code='en', value='Sale', status='published')
        resolved = resolve_translated_fields(self.doc, 'en')
        self.assertEqual(resolved['titulo'], 'Sale')
        self.assertEqual(resolved['descripcion'], 'Escritura')
        self.assertEqual(set(resolved), {'titulo', 'descripcion', 'notas'})

    def test_vocab_translation(self):
        tipo = self.doc.tipo_documento
        ct = ContentType.objects.get_for_model(TipoDocumental)
        Translation.objects.create(
            content_type=ct, object_id=tipo.pk, field_name='tipo_documental',
            language_code='en', value='Charter', status='published')
        self.assertEqual(get_translation(tipo, 'tipo_documental', 'en'), 'Charter')

    def test_mixin_inheritance_persona_esclavizada(self):
        fields = PersonaEsclavizada.get_translatable_fields()
        for name in ('notas', 'marcas_corporales', 'conducta', 'salud'):
            self.assertIn(name, fields)

    def test_leccion_translation_unique_lang(self):
        leccion = Leccion.objects.create(title='Lección', body='<p>Hola</p>')
        LeccionTranslation.objects.create(
            leccion=leccion, language_code='en', title='Lesson', body='Hello',
            status='published')
        with self.assertRaises(Exception):
            LeccionTranslation.objects.create(
                leccion=leccion, language_code='en', title='Dup', body='Dup')
        self.assertEqual(get_translation(leccion, 'title', 'en'), 'Lesson')
        self.assertEqual(get_translation(leccion, 'title', 'es'), 'Lección')

    def test_translation_save_refreshes_parent_vector(self):
        Documento.objects.filter(pk=self.doc.pk).update(search_vector=None)
        Translation.objects.create(
            content_type=self.ct, object_id=self.doc.pk, field_name='titulo',
            language_code='en', value='Sale of a house', status='published')
        doc = Documento.objects.get(pk=self.doc.pk)
        self.assertTrue(str(doc.search_vector or ''))


class ImportTranslationsCommandTests(TestCase):
    def setUp(self):
        archivo = Archivo.objects.create(nombre='Archivo Import')
        tipo = TipoDocumental.objects.create(tipo_documental='Acta')
        self.doc = Documento.objects.create(
            archivo=archivo, fondo='F', unidad_documental_compuesta='U',
            folio_inicial='1', tipo_documento=tipo, titulo='Acta de venta')

    def _csv(self, rows):
        fh = tempfile.NamedTemporaryFile(
            mode='w', suffix='.csv', delete=False, newline='', encoding='utf-8')
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        fh.close()
        return fh.name

    def test_csv_upsert_idempotent(self):
        from django.core.management import call_command
        path = self._csv([{
            'object_id': self.doc.pk, 'field_name': 'titulo',
            'language_code': 'en', 'value': 'Bill of sale'}])
        call_command('import_translations', model='documento', file=path)
        call_command('import_translations', model='documento', file=path)
        ct = ContentType.objects.get_for_model(Documento)
        self.assertEqual(Translation.objects.filter(
            content_type=ct, object_id=self.doc.pk).count(), 1)
        self.assertEqual(
            get_translation(Documento.objects.get(pk=self.doc.pk), 'titulo', 'es'),
            'Acta de venta')
        row = Translation.objects.get(content_type=ct, object_id=self.doc.pk)
        self.assertEqual(row.status, 'draft')

    def test_csv_publish_flag(self):
        from django.core.management import call_command
        path = self._csv([{
            'object_id': self.doc.pk, 'field_name': 'titulo',
            'language_code': 'en', 'value': 'Bill of sale', 'status': ''}])
        call_command('import_translations', model='documento', file=path, publish=True)
        self.assertEqual(
            get_translation(Documento.objects.get(pk=self.doc.pk), 'titulo', 'en'),
            'Bill of sale')


class SeedVocabTranslationsTests(TestCase):
    def test_fill_when_empty_never_overwrites(self):
        from django.core.management import call_command
        tipo = TipoDocumental.objects.create(tipo_documental='Carta de compra/venta')
        call_command('seed_vocab_translations_en')
        ct = ContentType.objects.get_for_model(TipoDocumental)
        row = Translation.objects.get(
            content_type=ct, object_id=tipo.pk, field_name='tipo_documental',
            language_code='en')
        self.assertEqual(row.status, 'draft')
        row.status = 'published'
        row.value = 'Team-edited value'
        row.save()
        call_command('seed_vocab_translations_en')
        row.refresh_from_db()
        self.assertEqual(row.status, 'published')
        self.assertEqual(row.value, 'Team-edited value')


class CrossLanguageSearchTests(TestCase):
    """Phase 2: published en translations are searchable via the english config."""

    def setUp(self):
        archivo = Archivo.objects.create(nombre='Archivo XLang')
        tipo = TipoDocumental.objects.create(tipo_documental='Carta de venta')
        self.doc = Documento.objects.create(
            archivo=archivo, fondo='F', unidad_documental_compuesta='U',
            folio_inicial='1', tipo_documento=tipo,
            titulo='Venta de una casa en Sevilla', descripcion='Escritura')

    def _publish(self, field, value, lang='en'):
        ct = ContentType.objects.get_for_model(Documento)
        Translation.objects.create(
            content_type=ct, object_id=self.doc.pk, field_name=field,
            language_code=lang, value=value, status='published')

    def test_english_query_hits_spanish_record(self):
        from django.contrib.postgres.search import SearchQuery
        self._publish('titulo', 'escaped slave sale')
        self.assertTrue(Documento.objects.filter(
            pk=self.doc.pk,
            search_vector=SearchQuery('escaped', config='english')).exists())
        self.assertTrue(Documento.objects.filter(
            pk=self.doc.pk,
            search_vector=SearchQuery('venta', config='spanish')).exists())

    def test_draft_translation_not_searchable(self):
        from django.contrib.postgres.search import SearchQuery
        ct = ContentType.objects.get_for_model(Documento)
        Translation.objects.create(
            content_type=ct, object_id=self.doc.pk, field_name='titulo',
            language_code='en', value='escaped slave sale', status='draft')
        self.assertFalse(Documento.objects.filter(
            pk=self.doc.pk,
            search_vector=SearchQuery('escaped', config='english')).exists())
