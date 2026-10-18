"""Phase 3 tests: ?lang= serving with fallback + workbench endpoint auth."""

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.test import APITestCase

from dbgestor.models import (
    Archivo, Documento, Leccion, LeccionTranslation,
    TipoDocumental, Translation,
)


class LangParamServingTests(APITestCase):
    def setUp(self):
        archivo = Archivo.objects.create(nombre='Archivo Lang')
        tipo = TipoDocumental.objects.create(tipo_documental='Carta de venta')
        self.doc = Documento.objects.create(
            archivo=archivo, fondo='F', unidad_documental_compuesta='U',
            folio_inicial='1', tipo_documento=tipo,
            titulo='Venta de una casa', descripcion='Escritura')
        ct = ContentType.objects.get_for_model(Documento)
        Translation.objects.create(
            content_type=ct, object_id=self.doc.pk, field_name='titulo',
            language_code='en', value='Sale of a house', status='published')
        self.url = f'/api/v2/documentos/{self.doc.pk}/'

    def test_default_spanish_unchanged(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()['titulo'], 'Venta de una casa')

    def test_english_resolves_published(self):
        resp = self.client.get(self.url, {'lang': 'en'})
        self.assertEqual(resp.json()['titulo'], 'Sale of a house')
        self.assertEqual(resp.json()['descripcion'], 'Escritura')

    def test_unsupported_lang_falls_back(self):
        resp = self.client.get(self.url, {'lang': 'xx'})
        self.assertEqual(resp.json()['titulo'], 'Venta de una casa')

    def test_vocab_lang_param(self):
        resp = self.client.get('/api/v2/vocabularios/tipos-documentales/', {'lang': 'en'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_leccion_lang_param(self):
        leccion = Leccion.objects.create(title='Lección', body='Hola', is_published=True)
        LeccionTranslation.objects.create(
            leccion=leccion, language_code='en', title='Lesson', body='Hello',
            status='published')
        resp = self.client.get(f'/api/v2/lecciones/{leccion.leccion_id}/', {'lang': 'en'})
        self.assertEqual(resp.json()['title'], 'Lesson')


class WorkbenchEndpointTests(APITestCase):
    def setUp(self):
        archivo = Archivo.objects.create(nombre='Archivo WB')
        tipo = TipoDocumental.objects.create(tipo_documental='Acta WB')
        self.doc = Documento.objects.create(
            archivo=archivo, fondo='F', unidad_documental_compuesta='U',
            folio_inicial='1', tipo_documento=tipo, titulo='Acta')
        self.staff = User.objects.create_user('wb_staff', password='x', is_staff=True)
        self.user = User.objects.create_user('wb_user', password='x')
        self.ct = ContentType.objects.get_for_model(Documento)

    def test_anonymous_forbidden(self):
        resp = self.client.get('/api/v2/workbench/translations/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_nonstaff_forbidden(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get('/api/v2/workbench/translations/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_crud_and_publish(self):
        self.client.force_authenticate(self.staff)
        resp = self.client.post('/api/v2/workbench/translations/', {
            'content_type': self.ct.pk, 'object_id': self.doc.pk,
            'field_name': 'titulo', 'language_code': 'en', 'value': 'Bill'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content[:300])
        row_id = resp.json()['id']
        self.assertEqual(resp.json()['status'], 'draft')
        resp = self.client.post(f'/api/v2/workbench/translations/{row_id}/publish/')
        self.assertEqual(resp.json()['status'], 'published')
        resp = self.client.get('/api/v2/workbench/translations/missing/', {
            'model': 'documento', 'field_name': 'titulo', 'language_code': 'en'})
        self.assertNotIn(self.doc.pk, resp.json()['missing_ids'])

    def test_staff_rejects_untranslatable_field(self):
        self.client.force_authenticate(self.staff)
        resp = self.client.post('/api/v2/workbench/translations/', {
            'content_type': self.ct.pk, 'object_id': self.doc.pk,
            'field_name': 'fondo', 'language_code': 'en', 'value': 'Fund'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
