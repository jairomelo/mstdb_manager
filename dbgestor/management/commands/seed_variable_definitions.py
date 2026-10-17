"""Seed the public data-dictionary registry (`VariableDefinition`).

Idempotent: creates missing rows and refreshes the structural fields
(modelo/clave/tipo/orden). Authored prose (`descripcion_es`/`descripcion_en`)
is only filled when empty, so team edits in the admin are never overwritten.

Usage:
    python manage.py seed_variable_definitions
    python manage.py seed_variable_definitions --overwrite-descriptions  # force reseed
"""

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from dbgestor.models import VariableDefinition


# (modelo, clave, tipo, orden, descripcion_es, descripcion_en)
REGISTRY = [
    # ---------------------------------------------------------------- Persona
    ('Persona', 'persona_idno', 'texto', 10,
     'Identificador estable de la persona en el proyecto (formato mx-sv-per-NNNNNN).',
     'Stable project identifier for the person (mx-sv-per-NNNNNN).'),
    ('Persona', 'nombres', 'texto', 20,
     'Nombres de la persona, sin honoríficos.', 'Given names, without honorifics.'),
    ('Persona', 'apellidos', 'texto', 30,
     'Apellidos de la persona.', 'Family names.'),
    ('Persona', 'nombre_normalizado', 'texto', 40,
     'Nombre completo normalizado usado para búsqueda y visualización.', 'Normalized full name used for search and display.'),
    ('Persona', 'sexo', 'vocabulario', 50,
     'Sexo registrado (Varón / Mujer / Desconocido).', 'Recorded sex (male / female / unknown).'),
    ('Persona', 'fecha_nacimiento', 'fecha', 60,
     'Fecha de nacimiento; puede ser aproximada (ver los campos _raw y _factual).', 'Birth date; may be approximate (see _raw and _factual variants).'),
    ('Persona', 'lugar_nacimiento', 'referencia (Lugar)', 70,
     'Lugar de nacimiento.', 'Place of birth.'),
    ('Persona', 'fecha_defuncion', 'fecha', 80,
     'Fecha de defunción; puede ser aproximada.', 'Death date; may be approximate.'),
    ('Persona', 'lugar_defuncion', 'referencia (Lugar)', 90,
     'Lugar de defunción.', 'Place of death.'),
    ('Persona', 'calidades', 'vocabulario (M2M)', 100,
     'Calidades jurídicas/sociales atribuidas a la persona.', 'Legal/social calidades attributed to the person.'),
    ('Persona', 'ocupaciones', 'vocabulario (M2M)', 110,
     'Oficios o actividades registradas.', 'Recorded occupations or activities.'),
    ('Persona', 'ocupacion_categoria', 'texto', 120,
     'Categoría de ocupación derivada.', 'Derived occupation category.'),
    ('Persona', 'estado_civil', 'vocabulario (M2M)', 130,
     'Estado civil registrado.', 'Recorded marital status.'),
    ('Persona', 'notas', 'texto', 140,
     'Notas de la persona en la base de datos original.', 'Free-text notes from the source database.'),
    ('Persona', 'documentos', 'referencia (M2M Documento)', 150,
     'Documentos que mencionan a la persona.', 'Documents that mention the person.'),
    ('Persona', 'is_published', 'booleano', 160,
     'Indica si el registro es público en la API.', 'Whether the record is publicly exposed in the API.'),

    # ---------------------------------------------------- PersonaEsclavizada
    ('PersonaEsclavizada', 'edad', 'entero', 10,
     'Edad registrada; la unidad está en unidad_temporal_edad.', 'Recorded age; the unit is in unidad_temporal_edad.'),
    ('PersonaEsclavizada', 'unidad_temporal_edad', 'vocabulario', 20,
     'Unidad de la edad: días / meses / años.', 'Age unit: days / months / years.'),
    ('PersonaEsclavizada', 'altura', 'texto', 30,
     'Estatura o descripción de la altura (texto original).', 'Height or height description (source text).'),
    ('PersonaEsclavizada', 'cabello', 'texto', 40,
     'Descripción del cabello (texto original).', 'Hair description (source text).'),
    ('PersonaEsclavizada', 'ojos', 'texto', 50,
     'Descripción de los ojos (texto original).', 'Eye description (source text).'),
    ('PersonaEsclavizada', 'marcas_corporales', 'texto', 60,
     'Marcas corporales, heridas o señales descritas en la fuente.', 'Body marks, wounds or distinguishing features described in the source.'),
    ('PersonaEsclavizada', 'conducta', 'texto', 70,
     'Conducta descrita en la fuente (texto libre; ver conducta_terms para la forma normalizada).', 'Conduct described in the source (free text; see conducta_terms for the normalized form).'),
    ('PersonaEsclavizada', 'salud', 'texto', 80,
     'Estado de salud descrito en la fuente.', 'Health state described in the source.'),
    ('PersonaEsclavizada', 'hispanizacion', 'vocabulario (M2M)', 90,
     'Grado de hispanización atribuido.', 'Attributed degree of Hispanicization.'),
    ('PersonaEsclavizada', 'etnonimos', 'vocabulario (M2M)', 100,
     'Etnónimos atribuidos en la fuente.', 'Ethnonyms attributed in the source.'),
    ('PersonaEsclavizada', 'conducta_terms', 'vocabulario (M2M)', 110,
     'Términos normalizados de conducta enlazados al texto libre.', 'Normalized conduct terms linked to the free text.'),
    ('PersonaEsclavizada', 'procedencia', 'referencia (Lugar)', 120,
     'Lugar de procedencia (origen) atribuido.', 'Attributed place of origin (procedencia).'),
    ('PersonaEsclavizada', 'procedencia_adicional', 'texto', 130,
     'Detalle adicional de procedencia no normalizado a un Lugar.', 'Additional origin detail not normalized to a Lugar.'),

    # ------------------------------------------------- PersonaNoEsclavizada
    ('PersonaNoEsclavizada', 'honorifico', 'vocabulario', 10,
     'Honorífico registrado (Don/Doña/…).', 'Recorded honorific (Don/Doña/…).'),
    ('PersonaNoEsclavizada', 'entidad_asociada', 'texto', 20,
     'Entidad asociada registrada como texto.', 'Associated entity recorded as text.'),

    # ---------------------------------------------------------- PersonaLugarRel
    ('PersonaLugarRel', 'personas', 'referencia (M2M Persona)', 10,
     'Personas vinculadas a esta relación con el lugar.', 'People linked to this place relationship.'),
    ('PersonaLugarRel', 'lugar', 'referencia (Lugar)', 20,
     'Lugar del evento de trayectoria.', 'Place of the trajectory event.'),
    ('PersonaLugarRel', 'documento', 'referencia (Documento)', 30,
     'Documento que documenta el evento.', 'Document that documents the event.'),
    ('PersonaLugarRel', 'situacion_lugar', 'vocabulario', 40,
     'Situación de la persona en el lugar (p. ej. residencia, tránsito).', 'Person\u2019s situation at the place (e.g. residence, transit).'),
    ('PersonaLugarRel', 'ordinal', 'entero', 50,
     'Orden secuencial del evento en la trayectoria vital de la persona.', 'Sequential order of the event in the person\u2019s life trajectory.'),
    ('PersonaLugarRel', 'fecha_inicial_lugar', 'fecha', 60,
     'Fecha inicial del evento en el lugar (puede ser aproximada).', 'Start date of the event at the place (may be approximate).'),
    ('PersonaLugarRel', 'fecha_final_lugar', 'fecha', 70,
     'Fecha final del evento en el lugar (puede ser aproximada).', 'End date of the event at the place (may be approximate).'),
    ('PersonaLugarRel', 'notas', 'texto', 80,
     'Notas sobre el evento.', 'Notes about the event.'),

    # ---------------------------------------------------------------- Documento
    ('Documento', 'titulo', 'texto', 10,
     'Título del documento.', 'Document title.'),
    ('Documento', 'fecha_inicial', 'fecha', 20,
     'Fecha inicial del documento.', 'Document start date.'),
    ('Documento', 'fecha_final', 'fecha', 30,
     'Fecha final del documento.', 'Document end date.'),
    ('Documento', 'lugar_de_produccion', 'referencia (Lugar)', 40,
     'Lugar donde se produjo el documento.', 'Place where the document was produced.'),
    ('Documento', 'archivo', 'referencia (Archivo)', 50,
     'Archivo que resguarda el documento.', 'Archive that holds the document.'),
    ('Documento', 'tipo_documental', 'vocabulario', 60,
     'Tipo documental (p. ej. carta de libertad, bautismo).', 'Document type (e.g. freedom letter, baptism).'),

    # -------------------------------------------------------------------- Lugar
    ('Lugar', 'nombre_lugar', 'texto', 10,
     'Nombre del lugar.', 'Place name.'),
    ('Lugar', 'otros_nombres', 'texto', 20,
     'Nombres alternativos o variantes del lugar.', 'Alternative names or variants of the place.'),
    ('Lugar', 'tipo', 'vocabulario', 30,
     'Tipo de lugar (ciudad, pueblo, real de minas, etc.).', 'Place type (city, town, mining real, etc.).'),
    ('Lugar', 'lat', 'decimal', 40,
     'Latitud geográfica.', 'Geographic latitude.'),
    ('Lugar', 'lon', 'decimal', 50,
     'Longitud geográfica.', 'Geographic longitude.'),
    ('Lugar', 'es_parte_de', 'referencia (Lugar)', 60,
     'Lugar superior del que depende jerárquicamente.', 'Parent place this one is part of.'),

    # -------------------------------------------------------------- Corporacion
    ('Corporacion', 'nombre', 'texto', 10,
     'Nombre de la corporación o institución.', 'Name of the corporation or institution.'),
    ('Corporacion', 'lugar_corporacion', 'referencia (Lugar)', 20,
     'Lugar de la corporación.', 'Place of the corporation.'),
    ('Corporacion', 'tipo_institucion', 'vocabulario', 30,
     'Tipo de institución.', 'Institution type.'),
]


class Command(BaseCommand):
    help = 'Seed/refresh the public data-dictionary (VariableDefinition) registry.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--overwrite-descriptions', action='store_true',
            help='Overwrite authored descriptions with the seed values.')

    def handle(self, *args, **options):
        overwrite = options['overwrite_descriptions']
        created = updated = 0
        for modelo, clave, tipo, orden, desc_es, desc_en in REGISTRY:
            variable_id = slugify(f'{modelo}-{clave}')[:150]
            obj, was_created = VariableDefinition.objects.get_or_create(
                variable_id=variable_id,
                defaults={
                    'modelo': modelo, 'clave': clave, 'tipo': tipo, 'orden': orden,
                    'descripcion_es': desc_es, 'descripcion_en': desc_en,
                },
            )
            if was_created:
                created += 1
                continue
            changed = False
            for field, value in (('modelo', modelo), ('clave', clave),
                                 ('tipo', tipo), ('orden', orden)):
                if getattr(obj, field) != value:
                    setattr(obj, field, value)
                    changed = True
            if overwrite:
                if obj.descripcion_es != desc_es:
                    obj.descripcion_es = desc_es
                    changed = True
                if obj.descripcion_en != desc_en:
                    obj.descripcion_en = desc_en
                    changed = True
            else:
                if not obj.descripcion_es:
                    obj.descripcion_es = desc_es
                    changed = True
                if not obj.descripcion_en:
                    obj.descripcion_en = desc_en
                    changed = True
            if changed:
                obj.save()
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'VariableDefinition seed complete: {created} created, {updated} updated.'))
