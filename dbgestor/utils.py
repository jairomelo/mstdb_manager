from .models import PersonaNoEsclavizada, PersonaEsclavizada, PersonaRelaciones


def derive_subordination_rels(documento_id: int) -> int:
    """
    For a single document, creates PersonaRelaciones(naturaleza_relacion='sub') rows
    for each (PersonaNoEsclavizada × PersonaEsclavizada) pair linked to the document
    via the Persona.documentos M2M, skipping pairs that already have a 'sub' relation.

    Returns the number of newly created relations.
    """
    non_enslaved = list(
        PersonaNoEsclavizada.objects.filter(documentos=documento_id)
    )
    enslaved = list(
        PersonaEsclavizada.objects.filter(documentos=documento_id)
    )

    if not non_enslaved or not enslaved:
        return 0

    existing = set(
        PersonaRelaciones.objects
        .filter(documento_id=documento_id, naturaleza_relacion='sub')
        .values_list('persona_sujeto_id', 'personas__persona_id')
    )

    created = 0
    for sujeto in non_enslaved:
        for objeto in enslaved:
            if (sujeto.persona_id, objeto.persona_id) in existing:
                continue
            rel = PersonaRelaciones.objects.create(
                documento_id=documento_id,
                naturaleza_relacion='sub',
                persona_sujeto=sujeto,
            )
            rel.personas.set([sujeto, objeto])
            created += 1

    return created


def revert_subordination_rels(documento_id: int) -> int:
    """
    Deletes all auto-derived subordination relations for a document.
    Only targets 'sub' relations with no descripcion_relacion (manually created
    ones typically have a description).

    Returns the number of deleted relations.
    """
    qs = PersonaRelaciones.objects.filter(
        documento_id=documento_id,
        naturaleza_relacion='sub',
        descripcion_relacion__isnull=True,
    )
    count = qs.count()
    qs.delete()
    return count
