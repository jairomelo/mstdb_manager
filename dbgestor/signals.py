"""
PostgreSQL full-text search signal handlers.

Auto-update search_vector fields on model save.
Skips raw saves (loaddata/fixtures) — use populate_search_vectors command instead.
"""

from django.contrib.postgres.search import SearchVector
from django.db.models import F, Func, OuterRef, Subquery
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Lugar, Documento, Persona, PersonaEsclavizada, Corporacion


class Unaccent(Func):
    function = 'UNACCENT'
    arity = 1


def persona_search_vector_expression(include_conducta=False):
    """Search vector expression for Persona rows (search_vector lives on Persona).

    conducta and salud are PersonaEsclavizada (MTI child) fields and cannot be referenced
    directly from an UPDATE on the parent table; they are fetched via correlated
    subqueries and unaccented so variantes like huido/huído match the same token.
    """
    vec = (
        SearchVector('nombre_normalizado', weight='A', config='spanish') +
        SearchVector('nombres', weight='A', config='spanish') +
        SearchVector('apellidos', weight='A', config='spanish') +
        SearchVector('notas', weight='C', config='spanish') +
        SearchVector('ocupacion_categoria', weight='D', config='spanish')
    )
    if include_conducta:
        def child_field(name):
            return Subquery(
                PersonaEsclavizada.objects.filter(
                    persona_id=OuterRef('persona_id')
                ).values(name)[:1]
            )

        vec += SearchVector(Unaccent(child_field('conducta')), weight='D', config='spanish')
        vec += SearchVector(Unaccent(child_field('salud')), weight='C', config='spanish')
    return vec


@receiver(post_save, sender=Lugar)
def update_lugar_search_vector(sender, instance, raw=False, **kwargs):
    if raw:
        return
    Lugar.objects.filter(pk=instance.pk).update(
        search_vector=(
            SearchVector('nombre_lugar', weight='A', config='spanish') +
            SearchVector('otros_nombres', weight='B', config='spanish') +
            SearchVector('tipo', weight='C', config='spanish')
        )
    )


@receiver(post_save, sender=Documento)
def update_documento_search_vector(sender, instance, raw=False, **kwargs):
    if raw:
        return
    Documento.objects.filter(pk=instance.pk).update(
        search_vector=(
            SearchVector('titulo', weight='A', config='spanish') +
            SearchVector('descripcion', weight='B', config='spanish') +
            SearchVector('notas', weight='C', config='spanish') +
            SearchVector('sigla_documento', weight='D', config='spanish')
        )
    )


@receiver(post_save, sender=Persona)
def update_persona_search_vector(sender, instance, raw=False, **kwargs):
    if raw:
        return
    include_conducta = isinstance(instance, PersonaEsclavizada)
    Persona.objects.filter(persona_id=instance.persona_id).update(
        search_vector=persona_search_vector_expression(include_conducta)
    )


@receiver(post_save, sender=Corporacion)
def update_corporacion_search_vector(sender, instance, raw=False, **kwargs):
    if raw:
        return
    instance.__class__.objects.filter(pk=instance.pk).update(
        search_vector=(
            SearchVector('nombre_institucion', weight='A', config='spanish') +
            SearchVector('nombres_alternativos', weight='B', config='spanish') +
            SearchVector('notas', weight='C', config='spanish')
        )
    )
