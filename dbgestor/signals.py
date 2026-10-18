"""
PostgreSQL full-text search signal handlers.

Auto-update search_vector fields on model save.
Skips raw saves (loaddata/fixtures) — use populate_search_vectors command instead.
"""

from django.contrib.postgres.search import SearchVector
from django.contrib.contenttypes.models import ContentType
from django.db.models import F, Func, OuterRef, Subquery
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import (
    Lugar, Documento, Persona, PersonaEsclavizada, Corporacion,
    TipoDocumental, Translation, LeccionTranslation,
)


class Unaccent(Func):
    function = 'UNACCENT'
    arity = 1


def published_translations_subquery(model, pk_field, weight='C'):
    """Aggregate published Translation values for one row, as an english vector.

    Correlated on the outer row via ``pk_field`` (concrete PK column). When no
    published translation exists the subquery is NULL and contributes nothing.
    NOTE: do not wrap the subquery in Coalesce — it breaks OuterRef resolution
    inside UPDATE statements (FieldError: Cannot resolve keyword '').
    """
    from django.contrib.postgres.aggregates import StringAgg
    ct = ContentType.objects.get_for_model(model, for_concrete_model=False)
    agg = Translation.objects.filter(
        content_type=ct,
        object_id=OuterRef(pk_field),
        status='published',
    ).annotate(
        text=StringAgg('value', delimiter=' ')
    ).values('text')[:1]
    return SearchVector(Subquery(agg), weight=weight, config='english')


def lugar_search_vector_expression():
    return (
        SearchVector('nombre_lugar', weight='A', config='spanish') +
        SearchVector('otros_nombres', weight='B', config='spanish') +
        SearchVector('tipo', weight='C', config='spanish') +
        published_translations_subquery(Lugar, 'lugar_id')
    )


def corporacion_search_vector_expression():
    return (
        SearchVector('nombre_institucion', weight='A', config='spanish') +
        SearchVector('nombres_alternativos', weight='B', config='spanish') +
        SearchVector('notas', weight='C', config='spanish') +
        published_translations_subquery(Corporacion, 'corporacion_id')
    )


def documento_search_vector_expression():
    """Search vector expression for Documento rows.

    tipo_documento is a FK and cannot be referenced directly from an UPDATE;
    it is fetched via a correlated subquery, mirroring the conducta pattern.
    """
    return (
        SearchVector('titulo', weight='A', config='spanish') +
        SearchVector('descripcion', weight='B', config='spanish') +
        SearchVector('notas', weight='C', config='spanish') +
        SearchVector(
            Subquery(
                TipoDocumental.objects.filter(
                    pk=OuterRef('tipo_documento_id')
                ).values('tipo_documental')[:1]
            ),
            weight='C', config='spanish') +
        SearchVector('sigla_documento', weight='D', config='spanish') +
        published_translations_subquery(Documento, 'documento_id')
    )


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
        SearchVector('ocupacion_categoria', weight='D', config='spanish') +
        published_translations_subquery(Persona, 'persona_id')
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
        search_vector=lugar_search_vector_expression()
    )


@receiver(post_save, sender=Documento)
def update_documento_search_vector(sender, instance, raw=False, **kwargs):
    if raw:
        return
    Documento.objects.filter(pk=instance.pk).update(
        search_vector=documento_search_vector_expression()
    )


@receiver(post_save, sender=TipoDocumental)
def update_documento_vectors_on_tipo_change(sender, instance, raw=False, **kwargs):
    if raw:
        return
    for doc_id in Documento.objects.filter(
            tipo_documento=instance).values_list('documento_id', flat=True):
        Documento.objects.filter(documento_id=doc_id).update(
            search_vector=documento_search_vector_expression()
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
        search_vector=corporacion_search_vector_expression()
    )


def refresh_search_vector(model, instance):
    """Recompute one row's search_vector (shared by entity + translation signals)."""
    from django.contrib.contenttypes.models import ContentType
    from . import models as _models

    if model is _models.Lugar:
        qs = _models.Lugar.objects.filter(pk=instance.pk)
        qs.update(search_vector=lugar_search_vector_expression())
    elif model is _models.Documento:
        qs = _models.Documento.objects.filter(pk=instance.pk)
        qs.update(search_vector=documento_search_vector_expression())
    elif model is _models.Corporacion:
        qs = _models.Corporacion.objects.filter(pk=instance.pk)
        qs.update(search_vector=corporacion_search_vector_expression())
    elif issubclass(model, _models.Persona):
        qs = _models.Persona.objects.filter(persona_id=instance.persona_id)
        qs.update(search_vector=persona_search_vector_expression(
            isinstance(instance, _models.PersonaEsclavizada)))
    elif model.__name__ == 'TipoDocumental':
        for doc_id in _models.Documento.objects.filter(
                tipo_documento=instance).values_list('documento_id', flat=True):
            _models.Documento.objects.filter(documento_id=doc_id).update(
                search_vector=documento_search_vector_expression())
    else:
        raise ValueError(f'No search_vector refresh rule for {model.__name__}')


def _has_search_vector(model):
    return any(f.name == 'search_vector' for f in model._meta.get_fields())


@receiver(post_save, sender=Translation)
def refresh_parent_on_translation_save(sender, instance, raw=False, **kwargs):
    if raw:
        return
    if instance.status != 'published':
        return
    parent_model = instance.content_type.model_class()
    if parent_model is None:
        return
    if parent_model is TipoDocumental:
        vocab = parent_model._default_manager.filter(pk=instance.object_id).first()
        if vocab is not None:
            refresh_search_vector(parent_model, vocab)
        return
    if not _has_search_vector(parent_model):
        return
    parent = parent_model._default_manager.filter(pk=instance.object_id).first()
    if parent is not None:
        refresh_search_vector(parent_model, parent)


@receiver(post_delete, sender=Translation)
def refresh_parent_on_translation_delete(sender, instance, **kwargs):
    parent_model = instance.content_type.model_class()
    if parent_model is None:
        return
    if parent_model is TipoDocumental:
        vocab = parent_model._default_manager.filter(pk=instance.object_id).first()
        if vocab is not None:
            refresh_search_vector(parent_model, vocab)
        return
    if not _has_search_vector(parent_model):
        return
    parent = parent_model._default_manager.filter(pk=instance.object_id).first()
    if parent is not None:
        refresh_search_vector(parent_model, parent)
