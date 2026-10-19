"""
PostgreSQL full-text search signal handlers.

Auto-update search_vector fields on model save.
Skips raw saves (loaddata/fixtures) — use populate_search_vectors command instead.
"""

from django.contrib.postgres.search import SearchVector
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import F, Func, OuterRef, Subquery
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import (
    Lugar, Documento, Persona, PersonaEsclavizada, Corporacion,
    TipoDocumental, Translation, LeccionTranslation,
    Calidades, Actividades, EstadoCivil, Hispanizaciones, Etonimos,
    ConductaTerm,
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


def linked_vocab_spanish_subquery(vocab_model, through_model, outer_field, vocab_fk, value_field):
    """Aggregate linked vocab terms (Spanish) for one persona row.

    Single-level correlation only: the term lookup references the through
    table, the through filter references the outer persona.
    """
    from django.contrib.postgres.aggregates import StringAgg
    sub = through_model.objects.filter(
        **{outer_field: OuterRef('persona_id')}
    ).annotate(
        term=Subquery(
            vocab_model.objects.filter(
                pk=OuterRef(vocab_fk)
            ).values(value_field)[:1]
        )
    ).values('term').annotate(
        text=StringAgg('term', delimiter=' ')
    ).values('text')[:1]
    return SearchVector(Subquery(sub), weight='C', config='spanish')


PERSONA_VOCAB_SPEC = None


def _persona_vocab_spec():
    """(vocab_model, through, outer_field, vocab_fk) for persona vectors."""
    global PERSONA_VOCAB_SPEC
    if PERSONA_VOCAB_SPEC is None:
        PERSONA_VOCAB_SPEC = [
            (Calidades, Persona.calidades.through, 'persona_id', 'calidades_id'),
            (Actividades, Persona.ocupaciones.through, 'persona_id', 'actividades_id'),
            (EstadoCivil, Persona.estado_civil.through, 'persona_id', 'estadocivil_id'),
            (Etonimos, PersonaEsclavizada.etnonimos.through,
             'personaesclavizada_id', 'etonimos_id'),
            (Hispanizaciones, PersonaEsclavizada.hispanizacion.through,
             'personaesclavizada_id', 'hispanizaciones_id'),
            (ConductaTerm, PersonaEsclavizada.conducta_terms.through,
             'personaesclavizada_id', 'conductaterm_id'),
        ]
    return PERSONA_VOCAB_SPEC


def persona_vocab_english_text(persona_id):
    """Published EN translations of all vocab terms linked to one persona.

    Computed in Python: the equivalent SQL needs double-nested correlation
    (Translation → through → outer persona), which Django cannot resolve
    inside UPDATE statements. Joined with spaces for the english vector.
    """
    texts = []
    for vocab_model, through, outer_field, vocab_fk in _persona_vocab_spec():
        linked = through.objects.filter(
            **{outer_field: persona_id}).values_list(vocab_fk, flat=True)
        linked = list(linked)
        if not linked:
            continue
        ct = ContentType.objects.get_for_model(vocab_model, for_concrete_model=False)
        values = Translation.objects.filter(
            content_type=ct, object_id__in=linked,
            status='published').values_list('value', flat=True)
        texts.extend(v for v in values if v)
    return ' '.join(texts)


def persona_search_vector_expression(include_conducta=False, vocab_en_text=''):
    """Search vector expression for Persona rows (search_vector lives on Persona).

    conducta and salud are PersonaEsclavizada (MTI child) fields and cannot be referenced
    directly from an UPDATE on the parent table; they are fetched via correlated
    subqueries and unaccented so variantes like huido/huído match the same token.

    Linked vocabularies (calidades, ocupaciones, estado civil, etnonimos,
    hispanizacion, conducta terms) join in Spanish via subqueries, plus their
    published English translations passed as ``vocab_en_text`` (see
    persona_vocab_english_text), so e.g. 'Cape Verde' hits a persona linked to
    'cabo verde'.
    """
    from django.db.models import Value
    vec = (
        SearchVector('nombre_normalizado', weight='A', config='spanish') +
        SearchVector('nombres', weight='A', config='spanish') +
        SearchVector('apellidos', weight='A', config='spanish') +
        SearchVector('notas', weight='C', config='spanish') +
        SearchVector('ocupacion_categoria', weight='D', config='spanish') +
        published_translations_subquery(Persona, 'persona_id')
    )
    _VOCAB_VALUES = {
        'Calidades': 'calidad', 'Actividades': 'actividad',
        'EstadoCivil': 'estado_civil', 'Etonimos': 'etonimo',
        'Hispanizaciones': 'hispanizacion', 'ConductaTerm': 'canonico',
    }
    for vocab_model, through, outer, fk in _persona_vocab_spec():
        vec += linked_vocab_spanish_subquery(
            vocab_model, through, outer, fk, _VOCAB_VALUES[vocab_model.__name__])
    if vocab_en_text:
        vec += SearchVector(Value(vocab_en_text, output_field=models.CharField()),
                            weight='C', config='english')
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
        search_vector=persona_search_vector_expression(
            include_conducta,
            vocab_en_text=persona_vocab_english_text(instance.persona_id))
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
            isinstance(instance, _models.PersonaEsclavizada),
            vocab_en_text=persona_vocab_english_text(instance.persona_id)))
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
    if _is_persona_vocab(parent_model):
        refresh_personas_linked_to_vocab(parent_model, instance.object_id)
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
    if _is_persona_vocab(parent_model):
        refresh_personas_linked_to_vocab(parent_model, instance.object_id)
        return
    if not _has_search_vector(parent_model):
        return
    parent = parent_model._default_manager.filter(pk=instance.object_id).first()
    if parent is not None:
        refresh_search_vector(parent_model, parent)


def _is_persona_vocab(model):
    return model in {Calidades, Actividades, EstadoCivil, Hispanizaciones, Etonimos, ConductaTerm}


def refresh_personas_linked_to_vocab(vocab_model, vocab_pk):
    """Refresh every persona vector linked to one vocab term (text/translation/M2M change)."""
    from . import models as _models
    for spec_model, through, outer_field, vocab_fk in _persona_vocab_spec():
        if spec_model is not vocab_model:
            continue
        pks = through.objects.filter(**{vocab_fk: vocab_pk}).values_list(outer_field, flat=True)
        for pid in set(pks):
            is_pe = _models.PersonaEsclavizada.objects.filter(persona_id=pid).exists()
            _models.Persona.objects.filter(persona_id=pid).update(
                search_vector=persona_search_vector_expression(
                    is_pe, vocab_en_text=persona_vocab_english_text(pid)))


def _refresh_persona_row(pid):
    from . import models as _models
    is_pe = _models.PersonaEsclavizada.objects.filter(persona_id=pid).exists()
    _models.Persona.objects.filter(persona_id=pid).update(
        search_vector=persona_search_vector_expression(
            is_pe, vocab_en_text=persona_vocab_english_text(pid)))


@receiver(post_save, sender=Calidades)
@receiver(post_save, sender=Actividades)
@receiver(post_save, sender=EstadoCivil)
@receiver(post_save, sender=Hispanizaciones)
@receiver(post_save, sender=Etonimos)
@receiver(post_save, sender=ConductaTerm)
def refresh_personas_on_vocab_save(sender, instance, raw=False, **kwargs):
    if raw:
        return
    refresh_personas_linked_to_vocab(sender, instance.pk)


from django.db.models.signals import m2m_changed as _m2m_changed


@_m2m_changed.connect
def refresh_persona_on_vocab_link_change(sender, instance, action, **kwargs):
    if action not in ('post_add', 'post_remove', 'post_clear'):
        return
    if sender not in {spec[1] for spec in _persona_vocab_spec()}:
        return
    pid = getattr(instance, 'persona_id', None)
    if pid is not None:
        _refresh_persona_row(pid)
