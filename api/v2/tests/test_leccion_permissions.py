"""Permission tests for the Leccion pipeline: draft/publish visibility,
creation gating (staff/colectores), owner/collaborator roles and access management."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APITestCase

from dbgestor.models import Leccion, LeccionAcceso

User = get_user_model()
BASE = '/api/v2/lecciones/'


class LeccionPermissionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user('staff_user', password='pw', is_staff=True)
        cls.colector = User.objects.create_user('colector_user', password='pw')
        colectores, _ = Group.objects.get_or_create(name='colectores')
        cls.colector.groups.add(colectores)
        cls.plain = User.objects.create_user('plain_user', password='pw')
        cls.collaborator = User.objects.create_user('collab_user', password='pw')

        cls.published = Leccion.objects.create(title='Publicada', body='<p>x</p>', is_published=True)
        cls.draft = Leccion.objects.create(title='Borrador', body='<p>y</p>', is_published=False)
        LeccionAcceso.objects.create(leccion=cls.draft, user=cls.colector, role='owner')
        LeccionAcceso.objects.create(leccion=cls.draft, user=cls.collaborator, role='collaborator')

    def _detail(self, leccion):
        return f'{BASE}{leccion.leccion_id}/'

    # ── Visibility ────────────────────────────────────────────────────────────

    def test_anonymous_sees_only_published(self):
        resp = self.client.get(BASE)
        ids = [r['leccion_id'] for r in resp.json()['results']]
        self.assertIn(self.published.leccion_id, ids)
        self.assertNotIn(self.draft.leccion_id, ids)

    def test_anonymous_cannot_open_draft(self):
        resp = self.client.get(self._detail(self.draft))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_plain_user_does_not_see_foreign_draft(self):
        self.client.force_authenticate(self.plain)
        resp = self.client.get(BASE)
        ids = [r['leccion_id'] for r in resp.json()['results']]
        self.assertNotIn(self.draft.leccion_id, ids)

    def test_owner_and_collaborator_see_draft(self):
        for user in (self.colector, self.collaborator):
            self.client.force_authenticate(user)
            resp = self.client.get(BASE)
            ids = [r['leccion_id'] for r in resp.json()['results']]
            self.assertIn(self.draft.leccion_id, ids)

    def test_staff_sees_everything(self):
        self.client.force_authenticate(self.staff)
        resp = self.client.get(BASE)
        ids = [r['leccion_id'] for r in resp.json()['results']]
        self.assertIn(self.published.leccion_id, ids)
        self.assertIn(self.draft.leccion_id, ids)

    def test_detail_permission_flags(self):
        self.client.force_authenticate(self.collaborator)
        data = self.client.get(self._detail(self.draft)).json()
        self.assertTrue(data['can_edit'])
        self.assertFalse(data['can_delete'])
        self.assertIn('accesos', data)

        self.client.force_authenticate(self.colector)
        data = self.client.get(self._detail(self.draft)).json()
        self.assertTrue(data['is_owner'])
        self.assertTrue(data['can_delete'])

    # ── Creation ──────────────────────────────────────────────────────────────

    def test_plain_user_cannot_create(self):
        self.client.force_authenticate(self.plain)
        resp = self.client.post(BASE, {'title': 'Nueva', 'body': ''}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_create(self):
        resp = self.client.post(BASE, {'title': 'Nueva', 'body': ''}, format='json')
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_colector_creates_draft_and_becomes_owner(self):
        self.client.force_authenticate(self.colector)
        resp = self.client.post(BASE, {'title': 'Nueva', 'body': '<p>hola</p>'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        leccion = Leccion.objects.get(pk=resp.json()['leccion_id'])
        self.assertFalse(leccion.is_published)
        self.assertEqual(leccion.created_by, self.colector)
        acceso = LeccionAcceso.objects.get(leccion=leccion, user=self.colector)
        self.assertEqual(acceso.role, 'owner')

    def test_staff_can_create(self):
        self.client.force_authenticate(self.staff)
        resp = self.client.post(BASE, {'title': 'Staff', 'body': ''}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    # ── Edit / publish / delete ───────────────────────────────────────────────

    def test_owner_can_edit_and_publish(self):
        self.client.force_authenticate(self.colector)
        resp = self.client.patch(self._detail(self.draft),
                                 {'title': 'Editada', 'is_published': True}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.draft.refresh_from_db()
        self.assertEqual(self.draft.title, 'Editada')
        self.assertTrue(self.draft.is_published)

    def test_collaborator_can_edit_content(self):
        self.client.force_authenticate(self.collaborator)
        resp = self.client.patch(self._detail(self.draft), {'title': 'Colab'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_collaborator_cannot_publish(self):
        self.client.force_authenticate(self.collaborator)
        resp = self.client.patch(self._detail(self.draft), {'is_published': True}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.draft.refresh_from_db()
        self.assertFalse(self.draft.is_published)

    def test_collaborator_cannot_delete(self):
        self.client.force_authenticate(self.collaborator)
        resp = self.client.delete(self._detail(self.draft))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_plain_user_cannot_edit(self):
        self.client.force_authenticate(self.plain)
        resp = self.client.patch(self._detail(self.published), {'title': 'x'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_delete(self):
        self.client.force_authenticate(self.colector)
        resp = self.client.delete(self._detail(self.draft))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    # ── Access management ─────────────────────────────────────────────────────

    def test_collaborator_cannot_manage_accesos(self):
        self.client.force_authenticate(self.collaborator)
        resp = self.client.post(f'{self._detail(self.draft)}accesos/agregar/',
                                {'username': 'plain_user', 'role': 'collaborator'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_adds_collaborator(self):
        self.client.force_authenticate(self.colector)
        resp = self.client.post(f'{self._detail(self.draft)}accesos/agregar/',
                                {'username': 'plain_user', 'role': 'collaborator'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            LeccionAcceso.objects.filter(leccion=self.draft, user=self.plain,
                                         role='collaborator').exists())

    def test_last_owner_removal_rejected(self):
        solo = Leccion.objects.create(title='Solo', is_published=False)
        acceso = LeccionAcceso.objects.create(leccion=solo, user=self.colector, role='owner')
        self.client.force_authenticate(self.colector)
        resp = self.client.delete(f'{BASE}{solo.leccion_id}/accesos/{acceso.leccion_acceso_id}/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_last_owner_demotion_rejected(self):
        solo = Leccion.objects.create(title='Solo2', is_published=False)
        acceso = LeccionAcceso.objects.create(leccion=solo, user=self.colector, role='owner')
        self.client.force_authenticate(self.colector)
        resp = self.client.patch(f'{BASE}{solo.leccion_id}/accesos/{acceso.leccion_acceso_id}/',
                                 {'role': 'collaborator'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ── User lookup ───────────────────────────────────────────────────────────

    def test_lookup_gated_and_no_email(self):
        resp = self.client.get('/api/v2/users/lookup/', {'username': 'pl'})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.plain)
        resp = self.client.get('/api/v2/users/lookup/', {'username': 'pl'})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.colector)
        resp = self.client.get('/api/v2/users/lookup/', {'username': 'pl'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        usernames = [r['username'] for r in resp.json()]
        self.assertIn('plain_user', usernames)
        self.assertNotIn('email', resp.json()[0])
