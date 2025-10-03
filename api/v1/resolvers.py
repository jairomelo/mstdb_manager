from dbgestor.models import (
    Lugar, Archivo, Documento, PersonaEsclavizada, PersonaNoEsclavizada,
    Calidades, Actividades, Hispanizaciones, Etonimos, EstadoCivil,
    PersonaLugarRel, PersonaRelaciones, RolEvento, PersonaRolEvento
)
from django.db import transaction
from django.utils.dateparse import parse_date
import re

import logging

logger = logging.getLogger("dbgestor")

def safe_strip(val):
    return val.strip() if isinstance(val, str) else ""

def safe_int(val):
    try:
        return int(re.findall(r'\d+', str(val))[0])
    except (IndexError, ValueError, TypeError):
        return None

def fecha_nacimiento(init_date, age):
    """
    Returns a date object based on the initial date and age.
    If age is not provided, returns None.
    """
    logger.debug(f"Calculating birth date from init_date: {init_date}, age: {age}")
    if not init_date or not isinstance(age, int) or age < 0:
        return None
    if not init_date or not age:
        return None
    try:
        date = parse_date(init_date)
        if date:
            logger.debug(f"Parsed date: {date}")
            return date.replace(year=date.year - age)
    except TypeError:
        logger.error(f"TYPEERROR: Invalid date format: {init_date}")
    except Exception as e:
        logger.error(f"Unexpected error while parsing date: {e}")
    return None

def get_or_create_lugar(nombre, tipo="ciudad", es_parte_de=None):
    if not nombre or not safe_strip(nombre):
        return None
    nombre = safe_strip(nombre)
    return Lugar.objects.get_or_create(
        nombre_lugar=nombre,
        tipo=tipo,
        es_parte_de=es_parte_de,
        defaults={"is_published": False}
    )[0]

def get_or_create_vocab(model, value):
    """
    Returns a list of model instances for the given comma-separated `value` string.
    Handles models with non-standard field names.
    """
    if not value:
        return []

    field_map = {
        'Calidades': 'calidad',
        'Actividades': 'actividad',
        'Hispanizaciones': 'hispanizacion',
        'Etonimos': 'etonimo',
        'EstadoCivil': 'estado_civil',
        'RolEvento': 'rol_evento',
    }

    model_name = model.__name__
    field_name = field_map.get(model_name)
    if not field_name:
        raise ValueError(f"No known field mapping for model {model_name}")

    objects = []
    for val in str(value).split(','):
        val = val.strip()
        if val:
            obj, _ = model.objects.get_or_create(**{field_name: val})
            objects.append(obj)
    return objects


def resolve_lugares(row):
    pais = get_or_create_lugar(row.get("archivo_pais"), "pais")
    estado = get_or_create_lugar(row.get("archivo_estado"), "estado", pais)
    ciudad = get_or_create_lugar(row.get("archivo_ciudad/pueblo"), "ciudad", estado)
    return {"pais": pais, "estado": estado, "ciudad": ciudad}

def resolve_archivo(row, lugares):
    nombre = safe_strip(row.get("archivo_nombre"))
    return Archivo.objects.get_or_create(
        nombre_abreviado=nombre,
        defaults={"ubicacion_archivo": lugares["ciudad"]}
    )[0]

def resolve_documento(row, archivo, lugares):
    return Documento.objects.create(
        archivo=archivo,
        fondo=row.get("archivo_fondo", ""),
        subfondo=row.get("archivo_subfondo"),
        titulo=row.get("asunto", "Documento sin título"),
        folio_inicial=row.get("fuente_folio", "1"),
        evento_valor_sp=row.get("evento_valor_sp"),
        evento_forma_de_pago=row.get("evento_forma_de_pago"),
        evento_total=row.get("evento_total"),
        fecha_inicial_raw=row.get("evento_fecha_completa [dd/mm/año]"),
        lugar_de_produccion=lugares["ciudad"],
        is_published=False
    )

def link_lugares_a_persona(persona, documento, row):
    mapping = [
        ("persona esclavizada_procedencia1", -4),
        ("persona esclavizada_procedencia2", -3),
        ("persona esclavizada_lugar_anterior_1 [nombre ciudad/distrito rural]", -2),
        ("persona esclavizada_lugar_anterior_2 [nombre ciudad/distrito rural]", -1),
        ("persona esclavizada_lugar_nuevo [nombre ciudad/distrito rural]", 1)
    ]
    for col, ordinal in mapping:
        lugar_name = row.get(col)
        if lugar_name:
            lugar = get_or_create_lugar(lugar_name)
            PersonaLugarRel.objects.create(
                documento=documento,
                lugar=lugar,
                ordinal=ordinal
            ).personas.add(persona)

def resolve_persona_esclavizada(row, documento):
    nombres = safe_strip(row.get("persona esclavizada_primer nombre")) or "Anónimo"
    apellidos = safe_strip(row.get("persona esclavizada_apellido"))
    nombre_normalizado = f"{nombres} {apellidos}".strip().title()

    persona = PersonaEsclavizada.objects.create(
        nombres=nombres,
        apellidos=apellidos,
        nombre_normalizado=nombre_normalizado,
        sexo="m" if "mujer" in safe_strip(row.get("persona esclavizada _sexo [varón/mujer]", "")).lower() else "v",
        edad=safe_int(row.get("persona esclavizada _edad")),
        fecha_nacimiento=fecha_nacimiento(
            row.get("evento_fecha_completa [dd/mm/año]"),
            safe_int(row.get("persona esclavizada _edad"))
        ),
        altura=row.get("persona esclavizada _altura"),
        cabello=row.get("persona esclavizada _cabello"),
        ojos=row.get("persona esclavizada _ojos"),
        ocupacion_categoria=row.get("persona esclavizada _ocupación_categoría"),
        is_published=False
    )
    persona.documentos.add(documento)

    persona.hispanizacion.set(get_or_create_vocab(Hispanizaciones, row.get("persona esclavizada _hispanización")))
    persona.etnonimos.set(get_or_create_vocab(Etonimos, row.get("persona esclavizada _etnónimo")))
    persona.estado_civil.set(get_or_create_vocab(EstadoCivil, row.get("persona esclavizada_estado civil")))
    persona.calidades.set(get_or_create_vocab(Calidades, row.get("persona esclavizada_calidades")))
    persona.ocupaciones.set(get_or_create_vocab(Actividades, row.get("persona esclavizada_ocupación")))

    link_lugares_a_persona(persona, documento, row)
    return persona

def resolve_persona_no_esclavizada(idx, row, documento):
    key_prefix = f"persona {idx}_"
    if not safe_strip(row.get(f"{key_prefix}primer nombre")):
        return None

    nombres = safe_strip(row.get(f"{key_prefix}primer nombre"))
    apellidos = safe_strip(row.get(f"{key_prefix}apellido"))
    nombre_normalizado = f"{nombres} {apellidos}".strip().title()

    persona = PersonaNoEsclavizada.objects.create(
        nombres=nombres,
        apellidos=apellidos,
        nombre_normalizado=nombre_normalizado,
        sexo="m" if "mujer" in safe_strip(row.get(f"{key_prefix}sexo", "")).lower() else "v",
        honorifico=row.get(f"{key_prefix}honorifico", "nan"),
        ocupacion_categoria=row.get(f"{key_prefix}ocupación_categoría"),
        is_published=False
    )
    persona.documentos.add(documento)

    persona.calidades.set(get_or_create_vocab(Calidades, row.get(f"{key_prefix}calidades")))
    persona.estado_civil.set(get_or_create_vocab(EstadoCivil, row.get(f"{key_prefix}estado civil")))
    persona.ocupaciones.set(get_or_create_vocab(Actividades, row.get(f"{key_prefix}ocupación")))

    roles = row.get(f"{key_prefix}rol/función en el documento")
    if roles:
        for rol_text in roles.split(";"):
            rol_text = safe_strip(rol_text)
            if not rol_text:
                continue
            rol, _ = RolEvento.objects.get_or_create(rol_evento=rol_text)
            PersonaRolEvento.objects.create(documento=documento, rol_evento=rol).personas.add(persona)

    return persona

@transaction.atomic
def ingest_row(row):
    lugares = resolve_lugares(row)
    archivo = resolve_archivo(row, lugares)
    documento = resolve_documento(row, archivo, lugares)
    esclavizada = resolve_persona_esclavizada(row, documento)

    noesclavizadas = []
    for i in range(2, 6):
        p = resolve_persona_no_esclavizada(i, row, documento)
        if p:
            noesclavizadas.append(p)

    return {
        "lugares": lugares,
        "archivo": archivo,
        "documento": documento,
        "persona_esclavizada": esclavizada,
        "personas_no_esclavizadas": noesclavizadas
    }
