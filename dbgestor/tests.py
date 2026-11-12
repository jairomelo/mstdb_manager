"""Regression tests for polymorphic model behavior on django-polymorphic 4.x."""

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from dbgestor.models import (
    Corporacion, Persona, PersonaEsclavizada, PersonaNoEsclavizada,
    TiposInstitucion,
)


class PersonaPolymorphismTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.esclavizada = PersonaEsclavizada.objects.create(
            nombres='Ana', sexo='m', edad=30)
        cls.no_esclavizada = PersonaNoEsclavizada.objects.create(
            nombres='Juan', sexo='v', honorifico='don')

    def test_child_manager_sets_polymorphic_ctype(self):
        self.assertEqual(
            self.esclavizada.polymorphic_ctype,
            ContentType.objects.get_for_model(PersonaEsclavizada))
        self.assertEqual(
            self.no_esclavizada.polymorphic_ctype,
            ContentType.objects.get_for_model(PersonaNoEsclavizada))

    def test_parent_queryset_returns_child_instances(self):
        self.assertIsInstance(
            Persona.objects.get(pk=self.esclavizada.pk), PersonaEsclavizada)
        self.assertIsInstance(
            Persona.objects.get(pk=self.no_esclavizada.pk), PersonaNoEsclavizada)

    def test_instance_of_filters(self):
        self.assertEqual(
            Persona.objects.instance_of(PersonaEsclavizada).get().pk,
            self.esclavizada.pk)
        self.assertEqual(
            Persona.objects.not_instance_of(PersonaEsclavizada).get().pk,
            self.no_esclavizada.pk)

    def test_child_field_lookup_via_parent_manager(self):
        self.assertEqual(
            Persona.objects.get(personaesclavizada__edad=30).pk,
            self.esclavizada.pk)

    def test_history_tracks_child_updates(self):
        self.esclavizada.edad = 31
        self.esclavizada.save()
        self.assertEqual(
            list(self.esclavizada.history.values_list('edad', flat=True)[:2]),
            [31, 30])


class CorporacionPolymorphismTests(TestCase):
    def test_base_manager_sets_polymorphic_ctype(self):
        tipo = TiposInstitucion.objects.create(tipo='Convento test')
        corporacion = Corporacion.objects.create(
            nombre_institucion='Corporación test', tipo_institucion=tipo)
        self.assertEqual(
            corporacion.polymorphic_ctype,
            ContentType.objects.get_for_model(Corporacion))
        self.assertIsInstance(
            Corporacion.objects.get(pk=corporacion.pk), Corporacion)
