"""Tests for filter-aware ``typeCounts`` on the unified search endpoint.

Every tab badge must reflect the current query + filters, so ``typeCounts``
has to be computed with the same pipeline as the active result set. The
key invariant is ``typeCounts[active] == count`` for single-type requests,
and narrowing a filter must lower ``typeCounts[active]``.
"""

from rest_framework import status
from rest_framework.test import APITestCase

from dbgestor.models import PersonaEsclavizada

SEARCH = '/api/v2/search/'

ALL_TYPES = {
    'documento',
    'personaesclavizada',
    'personanoesclavizada',
    'lugar',
    'corporacion',
}


class SearchTypeCountsTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.maria_v = PersonaEsclavizada.objects.create(nombres='Maria', sexo='v')
        cls.ana_v = PersonaEsclavizada.objects.create(nombres='Ana', sexo='v')
        cls.maria_m = PersonaEsclavizada.objects.create(nombres='Maria', sexo='m')

    def test_browse_returns_all_type_keys(self):
        resp = self.client.get(SEARCH, {'type': 'personaesclavizada'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertEqual(set(data['typeCounts'].keys()), ALL_TYPES)

    def test_browse_active_count_matches_type_count(self):
        resp = self.client.get(SEARCH, {'type': 'personaesclavizada'})
        data = resp.json()
        self.assertEqual(data['count'], 3)
        self.assertEqual(data['typeCounts']['personaesclavizada'], data['count'])

    def test_browse_filter_narrows_type_count(self):
        resp = self.client.get(SEARCH, {'type': 'personaesclavizada'})
        unfiltered = resp.json()

        resp = self.client.get(SEARCH, {'type': 'personaesclavizada', 'sexo': 'v'})
        filtered = resp.json()

        self.assertEqual(filtered['typeCounts']['personaesclavizada'], filtered['count'])
        self.assertLess(
            filtered['typeCounts']['personaesclavizada'],
            unfiltered['typeCounts']['personaesclavizada'],
        )

    def test_search_active_count_matches_type_count(self):
        resp = self.client.get(SEARCH, {'type': 'personaesclavizada', 'q': 'maria'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertEqual(data['count'], 2)
        self.assertEqual(data['typeCounts']['personaesclavizada'], data['count'])

    def test_search_filter_narrows_type_count(self):
        resp = self.client.get(SEARCH, {'type': 'personaesclavizada', 'q': 'maria'})
        unfiltered = resp.json()

        resp = self.client.get(
            SEARCH, {'type': 'personaesclavizada', 'q': 'maria', 'sexo': 'v'})
        filtered = resp.json()

        self.assertEqual(filtered['count'], 1)
        self.assertEqual(filtered['typeCounts']['personaesclavizada'], filtered['count'])
        self.assertLess(
            filtered['typeCounts']['personaesclavizada'],
            unfiltered['typeCounts']['personaesclavizada'],
        )
