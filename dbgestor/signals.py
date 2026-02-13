"""
PostgreSQL full-text search signal handlers.

These signals automatically update search_vector fields when models are saved,
enabling full-text search across key text fields.
"""

from django.contrib.postgres.search import SearchVector
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Lugar, Documento, Persona, Corporacion


@receiver(post_save, sender=Lugar)
def update_lugar_search_vector(sender, instance, **kwargs):
    """Update search_vector for Lugar after save."""
    # Use SearchVector with weights: A (highest) to D (lowest)
    # This allows prioritizing certain fields in search results
    Lugar.objects.filter(pk=instance.pk).update(
        search_vector=(
            SearchVector('nombre_lugar', weight='A', config='spanish') +
            SearchVector('nombre_pais', weight='B', config='spanish') +
            SearchVector('nombre_region', weight='B', config='spanish') +
            SearchVector('sinonimos', weight='C', config='spanish') +
            SearchVector('notas', weight='D', config='spanish')
        )
    )


@receiver(post_save, sender=Documento)
def update_documento_search_vector(sender, instance, **kwargs):
    """Update search_vector for Documento after save."""
    Documento.objects.filter(pk=instance.pk).update(
        search_vector=(
            SearchVector('titulo', weight='A', config='spanish') +
            SearchVector('descripcion', weight='B', config='spanish') +
            SearchVector('tipo_documento__nombre', weight='C', config='spanish') +
            SearchVector('folio', weight='D', config='spanish')
        )
    )


@receiver(post_save, sender=Persona)
def update_persona_search_vector(sender, instance, **kwargs):
    """Update search_vector for Persona after save."""
    # Handle both base Persona and subclasses (PersonaEsclavizada, PersonaNoEsclavizada)
    instance.__class__.objects.filter(pk=instance.pk).update(
        search_vector=(
            SearchVector('nombre_normalizado', weight='A', config='spanish') +
            SearchVector('nombres', weight='A', config='spanish') +
            SearchVector('apellidos', weight='A', config='spanish') +
            SearchVector('notas', weight='C', config='spanish') +
            SearchVector('ocupacion_categoria', weight='D', config='spanish')
        )
    )


@receiver(post_save, sender=Corporacion)
def update_corporacion_search_vector(sender, instance, **kwargs):
    """Update search_vector for Corporacion after save."""
    instance.__class__.objects.filter(pk=instance.pk).update(
        search_vector=(
            SearchVector('nombre_institucion', weight='A', config='spanish') +
            SearchVector('nombres_alternativos', weight='B', config='spanish') +
            SearchVector('notas', weight='C', config='spanish')
        )
    )
