"""Tests for the travel-trajectories aggregated endpoint (Bug 4 / mapa-trayectorias).

Covers the performance params (limit_rutas, min_count, bbox), the place_detail
modal endpoint (Entrantes/Salientes) and the route_detail DB pre-filter.
"""

from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from dbgestor.models import (
    Documento, Archivo, Lugar, PersonaEsclavizada, PersonaLugarRel, TipoDocumental,
)

AGG = '/api/v2/travel-trajectories/aggregated/'
ROUTE = '/api/v2/travel-trajectories/route_detail/'
PLACE = '/api/v2/travel-trajectories/place_detail/'


def _make_place(name, lat, lon):
    return Lugar.objects.create(nombre_lugar=name, lat=lat, lon=lon)


def _make_doc(archivo, fecha, tipo_doc):
    return Documento.objects.create(
        archivo=archivo, tipo_documento=tipo_doc, fondo='f', unidad_documental_compuesta='u',
        titulo=f'doc {fecha}', fecha_inicial=fecha, fecha_final=fecha,
    )


class AggregatedParamsTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cache.clear()
        cls.tipo_doc = TipoDocumental.objects.create(tipo_documental='Carta test bug4')
        cls.archivo = Archivo.objects.create(nombre='Archivo Test Bug4')
        cls.a = _make_place('Lugar A', 19.0, -99.0)
        cls.b = _make_place('Lugar B', 20.0, -100.0)
        cls.c = _make_place('Lugar C', 21.0, -101.0)
        cls.p1 = PersonaEsclavizada.objects.create(nombres='P1', sexo='v')
        cls.p2 = PersonaEsclavizada.objects.create(nombres='P2', sexo='m')
        doc1 = _make_doc(cls.archivo, '1700-01-01', cls.tipo_doc)
        doc2 = _make_doc(cls.archivo, '1701-01-01', cls.tipo_doc)
        cls.p1.documentos.add(doc1)
        cls.p2.documentos.add(doc2)
        PersonaLugarRel.objects.create(documento=doc1, lugar=cls.a, ordinal=0).personas.add(cls.p1)
        PersonaLugarRel.objects.create(documento=doc1, lugar=cls.b, ordinal=1).personas.add(cls.p1)
        PersonaLugarRel.objects.create(documento=doc2, lugar=cls.a, ordinal=0).personas.add(cls.p2)
        PersonaLugarRel.objects.create(documento=doc2, lugar=cls.c, ordinal=1).personas.add(cls.p2)

    def setUp(self):
        cache.clear()

    def test_aggregated_returns_routes_and_places(self):
        resp = self.client.get(AGG, {'include_timeline': '1'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertEqual(data['total_routes'], 2)
        self.assertEqual(data['total_places'], 3)
        self.assertFalse(data['truncated'])
        self.assertEqual(data['limit_rutas'], 500)

    def test_limit_rutas_truncates_and_reports(self):
        resp = self.client.get(AGG, {'limit_rutas': '1'})
        data = resp.json()
        self.assertEqual(len(data['routes']), 1)
        self.assertTrue(data['truncated'])
        self.assertEqual(data['limit_rutas'], 1)

    def test_min_count_filters_weak_routes(self):
        # A->B has count 1 here; with min_count=2 both routes disappear
        resp = self.client.get(AGG, {'min_count': '2'})
        data = resp.json()
        self.assertEqual(data['total_routes'], 0)
        self.assertEqual(data['total_places'], 0)

    def test_bbox_keeps_touching_routes(self):
        # Box around B only: A->B touches it, A->C does not
        resp = self.client.get(AGG, {'bbox': '-100.5,19.5,-99.5,20.5'})
        data = resp.json()
        pairs = {(r['from_lugar_id'], r['to_lugar_id']) for r in data['routes']}
        self.assertIn((self.a.lugar_id, self.b.lugar_id), pairs)
        self.assertNotIn((self.a.lugar_id, self.c.lugar_id), pairs)

    def test_invalid_params_return_400(self):
        for params in ({'limit_rutas': 'abc'}, {'min_count': 'x'}, {'bbox': '1,2,3'}):
            with self.subTest(params=params):
                resp = self.client.get(AGG, params)
                self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_route_detail_prefilter(self):
        resp = self.client.get(ROUTE, {
            'from_lugar_id': self.a.lugar_id, 'to_lugar_id': self.b.lugar_id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [r['persona_id'] for r in resp.json()['results']]
        self.assertIn(self.p1.persona_id, ids)
        self.assertNotIn(self.p2.persona_id, ids)

    def test_place_detail_directions(self):
        base = {'lugar_id': self.b.lugar_id}
        resp = self.client.get(PLACE, {**base, 'direction': 'in'})
        data = resp.json()
        ids = [r['persona_id'] for r in data['results']]
        self.assertIn(self.p1.persona_id, ids)
        self.assertNotIn(self.p2.persona_id, ids)
        self.assertEqual(data['incoming'], 1)
        self.assertEqual(data['outgoing'], 0)

        resp = self.client.get(PLACE, {'lugar_id': self.a.lugar_id, 'direction': 'out'})
        data = resp.json()
        ids = [r['persona_id'] for r in data['results']]
        self.assertIn(self.p1.persona_id, ids)
        self.assertIn(self.p2.persona_id, ids)

        resp = self.client.get(PLACE, {'lugar_id': 999999})
        self.assertEqual(resp.json()['count'], 0)

    def test_place_detail_requires_lugar_id(self):
        resp = self.client.get(PLACE)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        resp = self.client.get(PLACE, {'lugar_id': self.a.lugar_id, 'direction': 'sideways'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
