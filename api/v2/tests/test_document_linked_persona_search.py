"""Tests for document-linked persona expansion in unified search.

A text search returns, besides direct matches, every PE/PNE person linked
to an FTS-matched document (match_reason="documento"). Documents expose
per-document PE/PNE counts.
"""

from rest_framework import status
from rest_framework.test import APITestCase

from dbgestor.models import (
    Archivo, Documento, PersonaEsclavizada, PersonaNoEsclavizada, TipoDocumental,
)

SEARCH = '/api/v2/search/'


class DocumentLinkedPersonaSearchTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        archivo = Archivo.objects.create(nombre='Archivo Test')
        tipo = TipoDocumental.objects.create(tipo_documental='Carta de libertad')
        cls.doc = Documento.objects.create(
            archivo=archivo, fondo='F', unidad_documental_compuesta='U',
            folio_inicial='1', tipo_documento=tipo,
            titulo='Venta de una casa en Sevilla',
            descripcion='Escritura sobre una libertad otorgada',
        )
        cls.pe = PersonaEsclavizada.objects.create(nombres='Pedro', sexo='m')
        cls.pe.documentos.add(cls.doc)
        cls.pne = PersonaNoEsclavizada.objects.create(nombres='Juana', sexo='v')
        cls.pne.documentos.add(cls.doc)
        cls.unlinked = PersonaEsclavizada.objects.create(nombres='Zacarías', sexo='m')

    def test_linked_personas_returned_with_documento_reason(self):
        resp = self.client.get(SEARCH, {'type': 'personaesclavizada', 'q': 'libertad'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        ids = {r['source']['persona_id']: r.get('match_reason') for r in data['results']}
        self.assertIn(self.pe.persona_id, ids)
        self.assertEqual(ids[self.pe.persona_id], 'documento')
        self.assertNotIn(self.unlinked.persona_id, ids)
        self.assertEqual(data['typeCounts']['personaesclavizada'], data['count'])

    def test_direct_match_labeled_directo(self):
        self.pe.nombres = 'Libertad'
        self.pe.nombre_normalizado = 'Libertad'
        self.pe.save()
        from django.contrib.postgres.search import SearchVector
        from dbgestor.models import Persona
        Persona.objects.filter(pk=self.pe.pk).update(
            search_vector=(
                SearchVector('nombre_normalizado', weight='A', config='spanish') +
                SearchVector('nombres', weight='A', config='spanish')
            )
        )
        resp = self.client.get(SEARCH, {'type': 'personaesclavizada', 'q': 'libertad'})
        data = resp.json()
        ids = {r['source']['persona_id']: r.get('match_reason') for r in data['results']}
        self.assertEqual(ids[self.pe.persona_id], 'directo')
        self.assertEqual(
            sum(1 for r in data['results'] if r['source']['persona_id'] == self.pe.persona_id), 1)

    def test_document_counts(self):
        resp = self.client.get(SEARCH, {'type': 'documento', 'q': 'libertad'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        row = next(r for r in data['results'] if r['source']['documento_id'] == self.doc.documento_id)
        self.assertEqual(row['source']['personas_esclavizadas_count'], 1)
        self.assertEqual(row['source']['personas_no_esclavizadas_count'], 1)

    def test_tipo_rename_refreshes_vector(self):
        tipo = self.doc.tipo_documento
        tipo.tipo_documental = 'Manumisión solemne'
        tipo.save()
        doc = Documento.objects.get(pk=self.doc.pk)
        self.assertIn('manumision', str(doc.search_vector).lower())
