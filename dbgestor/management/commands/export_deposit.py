import csv
import itertools
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from dbgestor.version import get_schema_version
from dbgestor.models import (
    Actividades, Calidades, Corporacion, Documento, EstadoCivil,
    Etonimos, Hispanizaciones, InstitucionRolEvento, Lugar,
    PersonaEsclavizada, PersonaLugarRel, PersonaNoEsclavizada,
    PersonaRelaciones, PersonaRolEvento, RolEvento, SituacionLugar,
    TipoDocumental, TiposInstitucion,
    PLACE_TYPE_CHOICES,
)

PIPE = "|"


def _write_csv(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        count = 0
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


class Command(BaseCommand):
    help = "Exports a versioned deposit package (CSV files) to an output directory."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default="deposit",
            help="Root output directory (default: deposit/). A YYYY-MM-DD subfolder is created.",
        )

    def handle(self, *args, **options):
        today = date.today().isoformat()
        out_dir = Path(options["output"]) / today
        out_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write(f"Exporting deposit to {out_dir} ...")
        manifest = {}

        manifest.update(self._export_personas_esclavizadas(out_dir))
        manifest.update(self._export_personas_no_esclavizadas(out_dir))
        manifest.update(self._export_documentos(out_dir))
        manifest.update(self._export_lugares(out_dir))
        manifest.update(self._export_corporaciones(out_dir))
        manifest.update(self._export_trayectorias(out_dir))
        manifest.update(self._export_relaciones_personas(out_dir))
        manifest.update(self._export_roles_evento_personas(out_dir))
        manifest.update(self._export_roles_evento_instituciones(out_dir))
        manifest.update(self._export_codelists(out_dir))

        self._write_manifest(out_dir, manifest, today)
        self.stdout.write(self.style.SUCCESS(f"Done. {len(manifest)} files written to {out_dir}"))

    # -------------------------------------------------------------------------
    # Entity tables
    # -------------------------------------------------------------------------

    def _export_personas_esclavizadas(self, out_dir):
        fields = [
            "persona_idno", "nombres", "apellidos", "nombre_normalizado",
            "sexo", "edad", "unidad_temporal_edad", "altura", "cabello", "ojos",
            "calidades", "hispanizacion", "etnonimos",
            "procedencia_lugar_id", "procedencia_adicional",
            "marcas_corporales", "conducta", "salud",
            "ocupaciones", "ocupacion_categoria", "estado_civil",
            "lugar_nacimiento_id", "fecha_nacimiento", "fecha_nacimiento_raw",
            "fecha_nacimiento_factual", "lugar_defuncion_id",
            "fecha_defuncion", "fecha_defuncion_raw", "fecha_defuncion_factual",
            "documentos", "notas",
        ]

        def rows():
            qs = PersonaEsclavizada.objects.prefetch_related(
                "calidades", "hispanizacion", "etnonimos",
                "ocupaciones", "estado_civil", "documentos",
            ).select_related("procedencia", "lugar_nacimiento", "lugar_defuncion")
            for p in qs.iterator(chunk_size=2000):
                yield {
                    "persona_idno": p.persona_idno,
                    "nombres": p.nombres,
                    "apellidos": p.apellidos,
                    "nombre_normalizado": p.nombre_normalizado,
                    "sexo": p.sexo,
                    "edad": p.edad,
                    "unidad_temporal_edad": p.unidad_temporal_edad,
                    "altura": p.altura,
                    "cabello": p.cabello,
                    "ojos": p.ojos,
                    "calidades": PIPE.join(p.calidades.values_list("calidad", flat=True)),
                    "hispanizacion": PIPE.join(p.hispanizacion.values_list("hispanizacion", flat=True)),
                    "etnonimos": PIPE.join(p.etnonimos.values_list("etonimo", flat=True)),
                    "procedencia_lugar_id": p.procedencia_id,
                    "procedencia_adicional": p.procedencia_adicional,
                    "marcas_corporales": p.marcas_corporales,
                    "conducta": p.conducta,
                    "salud": p.salud,
                    "ocupaciones": PIPE.join(p.ocupaciones.values_list("actividad", flat=True)),
                    "ocupacion_categoria": p.ocupacion_categoria,
                    "estado_civil": PIPE.join(p.estado_civil.values_list("estado_civil", flat=True)),
                    "lugar_nacimiento_id": p.lugar_nacimiento_id,
                    "fecha_nacimiento": p.fecha_nacimiento,
                    "fecha_nacimiento_raw": p.fecha_nacimiento_raw,
                    "fecha_nacimiento_factual": p.fecha_nacimiento_factual,
                    "lugar_defuncion_id": p.lugar_defuncion_id,
                    "fecha_defuncion": p.fecha_defuncion,
                    "fecha_defuncion_raw": p.fecha_defuncion_raw,
                    "fecha_defuncion_factual": p.fecha_defuncion_factual,
                    "documentos": PIPE.join(p.documentos.values_list("documento_idno", flat=True)),
                    "notas": p.notas,
                }

        path = out_dir / "personas_esclavizadas.csv"
        count = _write_csv(path, fields, rows())
        self.stdout.write(f"  personas_esclavizadas.csv — {count} rows")
        return {"personas_esclavizadas.csv": count}

    def _export_personas_no_esclavizadas(self, out_dir):
        fields = [
            "persona_idno", "nombres", "apellidos", "nombre_normalizado",
            "sexo", "honorifico", "calidades", "ocupaciones", "ocupacion_categoria",
            "estado_civil", "entidad_asociada", "entidades_asociadas",
            "lugar_nacimiento_id", "fecha_nacimiento", "fecha_nacimiento_raw",
            "fecha_nacimiento_factual", "lugar_defuncion_id",
            "fecha_defuncion", "fecha_defuncion_raw", "fecha_defuncion_factual",
            "documentos", "notas",
        ]

        def rows():
            qs = PersonaNoEsclavizada.objects.prefetch_related(
                "calidades", "ocupaciones", "estado_civil",
                "documentos", "entidades_asociadas",
            ).select_related("lugar_nacimiento", "lugar_defuncion")
            for p in qs.iterator(chunk_size=2000):
                yield {
                    "persona_idno": p.persona_idno,
                    "nombres": p.nombres,
                    "apellidos": p.apellidos,
                    "nombre_normalizado": p.nombre_normalizado,
                    "sexo": p.sexo,
                    "honorifico": p.honorifico,
                    "calidades": PIPE.join(p.calidades.values_list("calidad", flat=True)),
                    "ocupaciones": PIPE.join(p.ocupaciones.values_list("actividad", flat=True)),
                    "ocupacion_categoria": p.ocupacion_categoria,
                    "estado_civil": PIPE.join(p.estado_civil.values_list("estado_civil", flat=True)),
                    "entidad_asociada": p.entidad_asociada,
                    "entidades_asociadas": PIPE.join(
                        p.entidades_asociadas.values_list("corporacion_idno", flat=True)
                    ),
                    "lugar_nacimiento_id": p.lugar_nacimiento_id,
                    "fecha_nacimiento": p.fecha_nacimiento,
                    "fecha_nacimiento_raw": p.fecha_nacimiento_raw,
                    "fecha_nacimiento_factual": p.fecha_nacimiento_factual,
                    "lugar_defuncion_id": p.lugar_defuncion_id,
                    "fecha_defuncion": p.fecha_defuncion,
                    "fecha_defuncion_raw": p.fecha_defuncion_raw,
                    "fecha_defuncion_factual": p.fecha_defuncion_factual,
                    "documentos": PIPE.join(p.documentos.values_list("documento_idno", flat=True)),
                    "notas": p.notas,
                }

        path = out_dir / "personas_no_esclavizadas.csv"
        count = _write_csv(path, fields, rows())
        self.stdout.write(f"  personas_no_esclavizadas.csv — {count} rows")
        return {"personas_no_esclavizadas.csv": count}

    def _export_documentos(self, out_dir):
        fields = [
            "documento_idno", "archivo_idno", "archivo_nombre",
            "archivo_nombre_abreviado", "archivo_ubicacion_lugar_id",
            "fondo", "subfondo", "serie", "subserie",
            "tipo_udc", "unidad_documental_compuesta",
            "tipo_documento", "sigla_documento", "titulo", "descripcion",
            "deteriorado", "fecha_inicial", "fecha_inicial_raw",
            "fecha_inicial_aproximada", "fecha_final", "fecha_final_raw",
            "fecha_final_aproximada", "lugar_de_produccion_id",
            "folio_inicial", "folio_final",
            "evento_valor_sp", "evento_forma_de_pago", "evento_total",
            "notas",
        ]

        def rows():
            qs = Documento.objects.select_related(
                "archivo", "archivo__ubicacion_archivo",
                "tipo_documento", "lugar_de_produccion",
            )
            for d in qs.iterator(chunk_size=2000):
                yield {
                    "documento_idno": d.documento_idno,
                    "archivo_idno": d.archivo.archivo_idno,
                    "archivo_nombre": d.archivo.nombre,
                    "archivo_nombre_abreviado": d.archivo.nombre_abreviado,
                    "archivo_ubicacion_lugar_id": d.archivo.ubicacion_archivo_id,
                    "fondo": d.fondo,
                    "subfondo": d.subfondo,
                    "serie": d.serie,
                    "subserie": d.subserie,
                    "tipo_udc": d.tipo_udc,
                    "unidad_documental_compuesta": d.unidad_documental_compuesta,
                    "tipo_documento": d.tipo_documento.tipo_documental if d.tipo_documento else None,
                    "sigla_documento": d.sigla_documento,
                    "titulo": d.titulo,
                    "descripcion": d.descripcion,
                    "deteriorado": d.deteriorado,
                    "fecha_inicial": d.fecha_inicial,
                    "fecha_inicial_raw": d.fecha_inicial_raw,
                    "fecha_inicial_aproximada": d.fecha_inicial_aproximada,
                    "fecha_final": d.fecha_final,
                    "fecha_final_raw": d.fecha_final_raw,
                    "fecha_final_aproximada": d.fecha_final_aproximada,
                    "lugar_de_produccion_id": d.lugar_de_produccion_id,
                    "folio_inicial": d.folio_inicial,
                    "folio_final": d.folio_final,
                    "evento_valor_sp": d.evento_valor_sp,
                    "evento_forma_de_pago": d.evento_forma_de_pago,
                    "evento_total": d.evento_total,
                    "notas": d.notas,
                }

        path = out_dir / "documentos.csv"
        count = _write_csv(path, fields, rows())
        self.stdout.write(f"  documentos.csv — {count} rows")
        return {"documentos.csv": count}

    def _export_lugares(self, out_dir):
        fields = [
            "lugar_id", "nombre_lugar", "otros_nombres", "tipo",
            "es_parte_de_lugar_id", "lat", "lon",
        ]

        def rows():
            for l in Lugar.objects.iterator(chunk_size=2000):
                yield {
                    "lugar_id": l.lugar_id,
                    "nombre_lugar": l.nombre_lugar,
                    "otros_nombres": l.otros_nombres,
                    "tipo": l.tipo,
                    "es_parte_de_lugar_id": l.es_parte_de_id,
                    "lat": l.lat,
                    "lon": l.lon,
                }

        path = out_dir / "lugares.csv"
        count = _write_csv(path, fields, rows())
        self.stdout.write(f"  lugares.csv — {count} rows")
        return {"lugares.csv": count}

    def _export_corporaciones(self, out_dir):
        fields = [
            "corporacion_idno", "nombre_institucion", "nombres_alternativos",
            "tipo_institucion", "lugar_corporacion_id",
            "personas_asociadas", "documentos", "notas",
        ]

        def rows():
            qs = Corporacion.objects.prefetch_related(
                "personas_asociadas", "documentos",
            ).select_related("tipo_institucion", "lugar_corporacion")
            for c in qs.iterator(chunk_size=2000):
                yield {
                    "corporacion_idno": c.corporacion_idno,
                    "nombre_institucion": c.nombre_institucion,
                    "nombres_alternativos": c.nombres_alternativos,
                    "tipo_institucion": c.tipo_institucion.tipo,
                    "lugar_corporacion_id": c.lugar_corporacion_id,
                    "personas_asociadas": PIPE.join(
                        c.personas_asociadas.values_list("persona_idno", flat=True)
                    ),
                    "documentos": PIPE.join(
                        c.documentos.values_list("documento_idno", flat=True)
                    ),
                    "notas": c.notas,
                }

        path = out_dir / "corporaciones.csv"
        count = _write_csv(path, fields, rows())
        self.stdout.write(f"  corporaciones.csv — {count} rows")
        return {"corporaciones.csv": count}

    # -------------------------------------------------------------------------
    # Relational tables
    # -------------------------------------------------------------------------

    def _export_trayectorias(self, out_dir):
        fields = [
            "persona_idno", "persona_x_lugares_id", "documento_idno",
            "lugar_id", "situacion_lugar", "ordinal",
            "fecha_inicial_lugar", "fecha_inicial_lugar_raw", "fecha_inicial_lugar_factual",
            "fecha_final_lugar", "fecha_final_lugar_raw", "fecha_final_lugar_factual",
            "notas",
        ]

        def rows():
            qs = PersonaLugarRel.objects.prefetch_related("personas").select_related(
                "documento", "lugar", "situacion_lugar"
            )
            for rel in qs.iterator(chunk_size=2000):
                doc_idno = rel.documento.documento_idno
                situacion = rel.situacion_lugar.situacion if rel.situacion_lugar else None
                for persona in rel.personas.all():
                    yield {
                        "persona_idno": persona.persona_idno,
                        "persona_x_lugares_id": rel.persona_x_lugares,
                        "documento_idno": doc_idno,
                        "lugar_id": rel.lugar_id,
                        "situacion_lugar": situacion,
                        "ordinal": rel.ordinal,
                        "fecha_inicial_lugar": rel.fecha_inicial_lugar,
                        "fecha_inicial_lugar_raw": rel.fecha_inicial_lugar_raw,
                        "fecha_inicial_lugar_factual": rel.fecha_inicial_lugar_factual,
                        "fecha_final_lugar": rel.fecha_final_lugar,
                        "fecha_final_lugar_raw": rel.fecha_final_lugar_raw,
                        "fecha_final_lugar_factual": rel.fecha_final_lugar_factual,
                        "notas": rel.notas,
                    }

        path = out_dir / "trayectorias.csv"
        count = _write_csv(path, fields, rows())
        self.stdout.write(f"  trayectorias.csv — {count} rows")
        return {"trayectorias.csv": count}

    def _export_relaciones_personas(self, out_dir):
        """Long/pairwise: one row per C(N,2) pair per PersonaRelaciones record."""
        fields = [
            "persona_idno_1", "persona_idno_2", "persona_relacion_id",
            "documento_idno", "naturaleza_relacion", "descripcion_relacion",
            "fecha_inicial_relacion", "fecha_inicial_relacion_raw",
            "fecha_inicial_relacion_factual", "fecha_final_relacion",
            "fecha_final_relacion_raw", "fecha_final_relacion_factual",
            "notas",
        ]

        def rows():
            qs = PersonaRelaciones.objects.prefetch_related("personas").select_related("documento")
            for rel in qs.iterator(chunk_size=2000):
                personas = list(rel.personas.all())
                doc_idno = rel.documento.documento_idno
                for p1, p2 in itertools.combinations(personas, 2):
                    yield {
                        "persona_idno_1": p1.persona_idno,
                        "persona_idno_2": p2.persona_idno,
                        "persona_relacion_id": rel.persona_relacion_id,
                        "documento_idno": doc_idno,
                        "naturaleza_relacion": rel.naturaleza_relacion,
                        "descripcion_relacion": rel.descripcion_relacion,
                        "fecha_inicial_relacion": rel.fecha_inicial_relacion,
                        "fecha_inicial_relacion_raw": rel.fecha_inicial_relacion_raw,
                        "fecha_inicial_relacion_factual": rel.fecha_inicial_relacion_factual,
                        "fecha_final_relacion": rel.fecha_final_relacion,
                        "fecha_final_relacion_raw": rel.fecha_final_relacion_raw,
                        "fecha_final_relacion_factual": rel.fecha_final_relacion_factual,
                        "notas": rel.notas,
                    }

        path = out_dir / "relaciones_personas.csv"
        count = _write_csv(path, fields, rows())
        self.stdout.write(f"  relaciones_personas.csv — {count} rows")
        return {"relaciones_personas.csv": count}

    def _export_roles_evento_personas(self, out_dir):
        fields = ["persona_idno", "documento_idno", "rol_evento"]

        def rows():
            qs = PersonaRolEvento.objects.prefetch_related("personas").select_related(
                "documento", "rol_evento"
            )
            for rol in qs.iterator(chunk_size=2000):
                doc_idno = rol.documento.documento_idno
                rol_nombre = rol.rol_evento.rol_evento
                for persona in rol.personas.all():
                    yield {
                        "persona_idno": persona.persona_idno,
                        "documento_idno": doc_idno,
                        "rol_evento": rol_nombre,
                    }

        path = out_dir / "roles_evento_personas.csv"
        count = _write_csv(path, fields, rows())
        self.stdout.write(f"  roles_evento_personas.csv — {count} rows")
        return {"roles_evento_personas.csv": count}

    def _export_roles_evento_instituciones(self, out_dir):
        fields = ["corporacion_idno", "documento_idno", "rol_evento"]

        def rows():
            qs = InstitucionRolEvento.objects.prefetch_related("corporaciones").select_related(
                "documento", "rol_evento"
            )
            for rol in qs.iterator(chunk_size=2000):
                doc_idno = rol.documento.documento_idno
                rol_nombre = rol.rol_evento.rol_evento
                for corp in rol.corporaciones.all():
                    yield {
                        "corporacion_idno": corp.corporacion_idno,
                        "documento_idno": doc_idno,
                        "rol_evento": rol_nombre,
                    }

        path = out_dir / "roles_evento_instituciones.csv"
        count = _write_csv(path, fields, rows())
        self.stdout.write(f"  roles_evento_instituciones.csv — {count} rows")
        return {"roles_evento_instituciones.csv": count}

    # -------------------------------------------------------------------------
    # Controlled vocabulary codelists
    # -------------------------------------------------------------------------

    def _export_codelists(self, out_dir):
        manifest = {}

        simple = [
            ("cv_calidades.csv", Calidades, ["calidad_id", "calidad", "descripcion"]),
            ("cv_etnonimos.csv", Etonimos, ["etonimo_id", "etonimo", "descripcion"]),
            ("cv_hispanizaciones.csv", Hispanizaciones, ["hispanizacion_id", "hispanizacion", "descripcion"]),
            ("cv_actividades.csv", Actividades, ["actividad_id", "actividad", "descripcion"]),
            ("cv_estados_civiles.csv", EstadoCivil, ["estado_civil", "descripcion"]),
            ("cv_tipos_documentales.csv", TipoDocumental, ["tipo_documental", "descripcion"]),
            ("cv_situaciones_lugar.csv", SituacionLugar, ["situacion_id", "situacion", "descripcion"]),
            ("cv_roles_evento.csv", RolEvento, ["rol_evento", "descripcion"]),
            ("cv_tipos_institucion.csv", TiposInstitucion, ["tipo_id", "tipo", "descripcion"]),
        ]

        for filename, model, fieldnames in simple:
            def make_rows(m, fn):
                for obj in m.objects.iterator(chunk_size=2000):
                    yield {f: getattr(obj, f, None) for f in fn}

            path = out_dir / filename
            count = _write_csv(path, fieldnames, make_rows(model, fieldnames))
            self.stdout.write(f"  {filename} — {count} rows")
            manifest[filename] = count

        # cv_tipos_lugar derives from model choices (not a DB table)
        lugar_fields = ["tipo", "etiqueta"]
        lugar_path = out_dir / "cv_tipos_lugar.csv"
        with open(lugar_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=lugar_fields)
            writer.writeheader()
            for code, label in PLACE_TYPE_CHOICES:
                writer.writerow({"tipo": code, "etiqueta": label})
        count = len(PLACE_TYPE_CHOICES)
        self.stdout.write(f"  cv_tipos_lugar.csv — {count} rows")
        manifest["cv_tipos_lugar.csv"] = count

        return manifest

    # -------------------------------------------------------------------------
    # Manifest
    # -------------------------------------------------------------------------

    def _write_manifest(self, out_dir, manifest, today):
        schema_version = get_schema_version()
        manifest_path = out_dir / "MANIFEST.txt"
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(f"TrayectoriasAfro Data Deposit\n")
            f.write(f"Export date    : {today}\n")
            f.write(f"Schema version : {schema_version}\n")
            f.write(f"License        : CC BY-NC 4.0\n")
            f.write(f"\nNote: 'Export date' is the data snapshot date. ")
            f.write(f"Schema version tracks structural changes to the CSV layout.\n")
            f.write(f"{'File':<45} {'Rows':>8}\n")
            f.write(f"{'-'*45} {'-'*8}\n")
            for filename, count in sorted(manifest.items()):
                f.write(f"{filename:<45} {count:>8}\n")
        self.stdout.write(f"  MANIFEST.txt written")
