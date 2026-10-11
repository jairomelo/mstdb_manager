"""
Data integrity audit between a ground-truth Lugar CSV export and the database.

Reads a CSV (default: temp/data/Lugar-2026-10-11.csv, columns as exported from
the cataloguing tool — lugar_id, nombre_lugar, lat, lon, comentarios, ...) and
compares it against the `dbgestor_lugar` table on `lugar_id` as primary key.

The CSV's `comentarios` column is a curator-annotation column that exists only
in the export, not in the database, so all comment-based categorization is done
from the CSV side.

Checks:
  1. Every CSV record: does the lugar_id exist in the DB, and do lat/lon match?
  2. Missing in CSV  — DB rows with no CSV counterpart (count + list).
  3. Missing in DB   — CSV lugar_ids absent from the database (count + list).
  4. Missing coords  — total records lacking lat/lon, split into:
       a. unreferenceable (comment semantics: etnónimo, "no puede ser
          referenciada", etc.) vs. plain missing data;
       b. whether DB agrees on the missingness.
  5. Consolidation hints in comentarios (consolidar/unificar/combinar/etc.).

Data-type robustness: lugar_id is coerced to int, lat/lon to Decimal (the DB
column is numeric(9,6)), empty strings are treated as NULL, and a tolerance
compares decimals so export rounding never produces false mismatches.

    python manage.py audit_lugar_csv
    python manage.py audit_lugar_csv --csv ../temp/data/Lugar-2026-10-11.csv --json report.json
"""

import csv
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from dbgestor.models import Lugar

# Decimal comparison tolerance: CSV exports and numeric(9,6) can round at the
# 6th decimal place.
COORD_TOLERANCE = Decimal("0.000001")

# Curator annotations marking a place that cannot be georeferenced on purpose
# (ethnic designations, broad regions, "cannot be referenced", ...).
UNREFERENCEABLE_MARKERS = (
    "etnonim",           # etnónimo / etnonimo
    "etnónim",
    "no puede ser referenciada",
    "no se puede ubicar",
    "no se debe considerar",
    "cannot be georeferenced",
    "cannot be referenced",
    "es muy general",
)

# Curator annotations marking places that should be merged into another record.
CONSOLIDATION_MARKERS = (
    "consolidar",
    "unificar",
    "combinar",
    "unir con",
    "merge",
)

COMMA_DECIMAL_RE = re.compile(r"^-?\d+,\d+$")


def parse_lugar_id(raw):
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        return int(float(s)) if "." in s else int(s)
    except (TypeError, ValueError):
        return None


def parse_coord(raw):
    """Parse a CSV coordinate cell to Decimal. Returns (value_or_None, had_value)."""
    if raw is None:
        return None, False
    s = str(raw).strip()
    if not s:
        return None, False
    if COMMA_DECIMAL_RE.match(s):
        s = s.replace(",", ".")
    try:
        return Decimal(s), True
    except (InvalidOperation, ValueError):
        return None, True  # present but unparseable


def to_decimal_or_none(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def normalize_text(text):
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def classify_comment(comment):
    """Return (is_unreferenceable, is_consolidation) for a comentarios cell."""
    norm = normalize_text(comment)
    if not norm:
        return False, False
    unref = any(marker in norm for marker in UNREFERENCEABLE_MARKERS)
    consol = any(marker in norm for marker in CONSOLIDATION_MARKERS)
    return unref, consol


class Command(BaseCommand):
    help = (
        "Audit a ground-truth Lugar CSV against the database: existence of each "
        "lugar_id, lat/lon agreement, missing records on either side, missing "
        "coordinates (with unreferenceable-comment categorization) and "
        "consolidation hints."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            type=str,
            default=None,
            help=(
                "Path to the ground-truth CSV. Default: temp/data/"
                "Lugar-<today>.csv at the repo root (parent of mstdb_manager)."
            ),
        )
        parser.add_argument(
            "--json",
            type=str,
            default=None,
            help="Optional path to write the full report as JSON.",
        )
        parser.add_argument(
            "--report",
            type=str,
            default=None,
            help="Optional path to write every finding as a flat CSV report.",
        )
        parser.add_argument(
            "--tolerance",
            type=str,
            default=str(COORD_TOLERANCE),
            help="Coordinate comparison tolerance (decimal, default 0.000001).",
        )

    # ------------------------------------------------------------------ util

    def _default_csv_candidates(self):
        """Possible temp/data locations across local and Docker layouts.

        Locally the repo root is the parent of mstdb_manager; inside the web
        container /app is mstdb_manager and the repo root may be mounted at
        /app/root (or not mounted at all — then pass --csv explicitly).
        """
        from datetime import date

        fname = f"Lugar-{date.today().isoformat()}.csv"
        here = Path(__file__).resolve()
        mstdb_manager = here.parents[3]  # .../mstdb_manager
        repo_root = mstdb_manager.parent
        return [
            repo_root / "temp" / "data" / fname,
            mstdb_manager.parent / "root" / "temp" / "data" / fname,
            Path("/app/root/temp/data") / fname,
            Path("/temp/data") / fname,
        ]

    def _resolve_csv(self, raw):
        if raw:
            path = Path(raw).expanduser()
            if not path.is_file():
                raise CommandError(f"CSV file not found: {path}")
            return path
        for candidate in self._default_csv_candidates():
            if candidate.is_file():
                return candidate
        searched = "\n  ".join(str(p) for p in self._default_csv_candidates())
        raise CommandError(
            "Could not locate the default Lugar CSV. Searched:\n  "
            f"{searched}\nPass --csv <path> explicitly."
        )

    @staticmethod
    def _load_csv(path):
        rows, issues = [], []
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or "lugar_id" not in reader.fieldnames:
                raise CommandError(
                    f"CSV must contain a 'lugar_id' column; found: {reader.fieldnames}"
                )
            for lineno, raw in enumerate(reader, start=2):
                raw_id = raw.get("lugar_id")
                lugar_id = parse_lugar_id(raw_id)
                if lugar_id is None:
                    issues.append({"line": lineno, "value": raw_id, "reason": "unparseable lugar_id"})
                    continue
                lat, lat_present = parse_coord(raw.get("lat"))
                lon, lon_present = parse_coord(raw.get("lon"))
                comments = (raw.get("comentarios") or "").strip()
                unref, consol = classify_comment(comments)
                rows.append({
                    "line": lineno,
                    "lugar_id": lugar_id,
                    "nombre_lugar": (raw.get("nombre_lugar") or "").strip(),
                    "lat": lat,
                    "lon": lon,
                    "lat_present": lat_present,
                    "lon_present": lon_present,
                    "comentarios": comments,
                    "unreferenceable": unref,
                    "consolidation": consol,
                })
        return rows, issues

    # ------------------------------------------------------------------ audit

    def handle(self, *args, **options):
        try:
            tolerance = Decimal(str(options["tolerance"]))
        except InvalidOperation:
            raise CommandError(f"Invalid --tolerance value: {options['tolerance']}")

        csv_path = self._resolve_csv(options["csv"])
        csv_rows, csv_issues = self._load_csv(csv_path)

        duplicates = self._find_duplicate_ids(csv_rows)

        db_by_id = {
            l.lugar_id: l
            for l in Lugar.objects.all().only("lugar_id", "nombre_lugar", "lat", "lon")
        }
        csv_by_id = {r["lugar_id"]: r for r in csv_rows}

        report = {
            "csv_path": str(csv_path),
            "tolerance": str(tolerance),
            "totals": {
                "csv_rows": len(csv_rows),
                "csv_unparseable_rows": len(csv_issues),
                "csv_duplicate_ids": len(duplicates),
                "db_rows": len(db_by_id),
            },
            "validation": {
                "matched": [],
                "coord_mismatch": [],
                "coord_partial_in_csv": [],
                "coord_mismatch_db_missing": [],
                "coord_mismatch_csv_missing": [],
                "name_mismatch": [],
            },
            "missing_in_csv": [],
            "missing_in_db": [],
            "missing_coordinates": {
                "csv": {"total": 0, "unreferenceable": [], "plain": []},
                "db": {"total": 0, "unreferenceable": [], "plain": []},
                "disagreements": [],
            },
            "consolidation": [],
            "parse_issues": csv_issues,
            "duplicate_ids": duplicates,
        }

        self._validate_existing(csv_rows, db_by_id, tolerance, report)
        self._collect_missing(csv_by_id, db_by_id, report)
        self._collect_missing_coordinates(csv_rows, db_by_id, report)
        self._collect_consolidation(csv_rows, report)

        self._render(report)

        if options["json"]:
            out = Path(options["json"]).expanduser()
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"JSON report written to {out}"))

        if options["report"]:
            out = Path(options["report"]).expanduser()
            out.parent.mkdir(parents=True, exist_ok=True)
            self._write_flat_csv(out, report)
            self.stdout.write(self.style.SUCCESS(f"CSV report written to {out}"))

    # ------------------------------------------------------------- outputs

    @staticmethod
    def _flat_rows(report):
        def row(section, detail, entry):
            return {
                "section": section,
                "detail": detail,
                "lugar_id": entry.get("lugar_id", ""),
                "nombre_lugar": entry.get("nombre_lugar", ""),
                "comentarios": entry.get("comentarios", ""),
                "csv_lat": entry.get("csv_lat", ""),
                "csv_lon": entry.get("csv_lon", ""),
                "db_lat": entry.get("db_lat", ""),
                "db_lon": entry.get("db_lon", ""),
                "mismatched_fields": ",".join(entry.get("mismatched_fields", [])),
                "note": entry.get("note", entry.get("reason", "")),
            }

        rows = []
        v = report["validation"]
        for section in ("coord_mismatch", "coord_mismatch_db_missing",
                        "coord_mismatch_csv_missing", "coord_partial_in_csv",
                        "name_mismatch"):
            for e in v[section]:
                rows.append(row("validation", section, e))
        for e in report["missing_in_csv"]:
            rows.append(row("missing_in_csv", "db_only", e))
        for e in report["missing_in_db"]:
            rows.append(row("missing_in_db", "csv_only", e))
        mc = report["missing_coordinates"]
        for side in ("csv", "db"):
            for key in ("unreferenceable", "plain"):
                for e in mc[side][key]:
                    rows.append(row("missing_coordinates", f"{side}_{key}", e))
        for e in mc["disagreements"]:
            rows.append(row("missing_coordinates", "disagreement", e))
        for e in report["consolidation"]:
            rows.append(row("consolidation", "hint", e))
        for e in report["parse_issues"]:
            rows.append(row("parse_issues", e["reason"], {"note": repr(e["value"])}))
        for e in report["duplicate_ids"]:
            rows.append(row("duplicate_ids", "repeat", e))
        return rows

    def _write_flat_csv(self, path, report):
        rows = self._flat_rows(report)
        fields = ["section", "detail", "lugar_id", "nombre_lugar", "comentarios",
                  "csv_lat", "csv_lon", "db_lat", "db_lon", "mismatched_fields", "note"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    # ------------------------------------------------------------- sections

    @staticmethod
    def _find_duplicate_ids(rows):
        seen, dups = set(), []
        for r in rows:
            if r["lugar_id"] in seen:
                dups.append({"lugar_id": r["lugar_id"], "line": r["line"]})
            seen.add(r["lugar_id"])
        return dups

    def _validate_existing(self, csv_rows, db_by_id, tolerance, report):
        v = report["validation"]
        for row in csv_rows:
            db = db_by_id.get(row["lugar_id"])
            if db is None:
                continue  # handled under missing_in_db

            db_lat = to_decimal_or_none(db.lat)
            db_lon = to_decimal_or_none(db.lon)
            entry = {
                "lugar_id": row["lugar_id"],
                "nombre_lugar": row["nombre_lugar"],
                "db_nombre_lugar": db.nombre_lugar,
                "csv_lat": str(row["lat"]) if row["lat"] is not None else None,
                "csv_lon": str(row["lon"]) if row["lon"] is not None else None,
                "db_lat": str(db_lat) if db_lat is not None else None,
                "db_lon": str(db_lon) if db_lon is not None else None,
            }

            csv_has_both = row["lat"] is not None and row["lon"] is not None
            csv_has_any = row["lat"] is not None or row["lon"] is not None
            db_has_both = db_lat is not None and db_lon is not None

            if row["lat_present"] != (row["lat"] is not None) or row["lon_present"] != (row["lon"] is not None):
                entry["note"] = "CSV coordinate present but unparseable"
                v["coord_partial_in_csv"].append(entry)
                continue

            if not csv_has_any and not db_has_both and (db_lat is None and db_lon is None):
                v["matched"].append(entry)
                continue

            if csv_has_both and db_has_both:
                lat_ok = abs(row["lat"] - db_lat) <= tolerance
                lon_ok = abs(row["lon"] - db_lon) <= tolerance
                if lat_ok and lon_ok:
                    v["matched"].append(entry)
                else:
                    entry["mismatched_fields"] = [
                        f for f, ok in (("lat", lat_ok), ("lon", lon_ok)) if not ok
                    ]
                    v["coord_mismatch"].append(entry)
            elif csv_has_both and not db_has_both:
                v["coord_mismatch_db_missing"].append(entry)
            elif not csv_has_both and db_has_both:
                v["coord_mismatch_csv_missing"].append(entry)
            else:
                # Partial data on one/both sides
                v["coord_partial_in_csv"].append(entry)

            if normalize_text(row["nombre_lugar"]) != normalize_text(db.nombre_lugar):
                v["name_mismatch"].append(entry)

    @staticmethod
    def _collect_missing(csv_by_id, db_by_id, report):
        for lugar_id in sorted(set(csv_by_id) - set(db_by_id)):
            r = csv_by_id[lugar_id]
            report["missing_in_db"].append({
                "lugar_id": lugar_id,
                "nombre_lugar": r["nombre_lugar"],
                "comentarios": r["comentarios"],
            })
        for lugar_id in sorted(set(db_by_id) - set(csv_by_id)):
            db = db_by_id[lugar_id]
            report["missing_in_csv"].append({
                "lugar_id": lugar_id,
                "nombre_lugar": db.nombre_lugar,
            })

    def _collect_missing_coordinates(self, csv_rows, db_by_id, report):
        mc = report["missing_coordinates"]

        for row in csv_rows:
            if row["lat"] is not None and row["lon"] is not None:
                continue
            bucket = mc["csv"]
            bucket["total"] += 1
            entry = {
                "lugar_id": row["lugar_id"],
                "nombre_lugar": row["nombre_lugar"],
                "comentarios": row["comentarios"],
                "reason": row["comentarios"] if row["unreferenceable"] else None,
            }
            key = "unreferenceable" if row["unreferenceable"] else "plain"
            bucket[key].append(entry)

            db = db_by_id.get(row["lugar_id"])
            if db is not None:
                db_lat = to_decimal_or_none(db.lat)
                db_lon = to_decimal_or_none(db.lon)
                db_missing = db_lat is None or db_lon is None
                csv_missing = row["lat"] is None or row["lon"] is None
                if db_missing != csv_missing:
                    mc["disagreements"].append({
                        "lugar_id": row["lugar_id"],
                        "nombre_lugar": row["nombre_lugar"],
                        "csv_missing": csv_missing,
                        "db_missing": db_missing,
                    })

        for lugar_id, db in sorted(db_by_id.items()):
            db_lat = to_decimal_or_none(db.lat)
            db_lon = to_decimal_or_none(db.lon)
            if db_lat is not None and db_lon is not None:
                continue
            bucket = mc["db"]
            bucket["total"] += 1
            csv_row = next((r for r in csv_rows if r["lugar_id"] == lugar_id), None)
            comment = csv_row["comentarios"] if csv_row else ""
            unref = csv_row["unreferenceable"] if csv_row else False
            entry = {
                "lugar_id": lugar_id,
                "nombre_lugar": db.nombre_lugar,
                "comentarios": comment,
                "reason": comment if unref else None,
            }
            key = "unreferenceable" if unref else "plain"
            bucket[key].append(entry)

            if csv_row is not None:
                csv_missing = csv_row["lat"] is None or csv_row["lon"] is None
                db_missing = True
                if csv_missing != db_missing:
                    mc["disagreements"].append({
                        "lugar_id": lugar_id,
                        "nombre_lugar": csv_row["nombre_lugar"],
                        "csv_missing": csv_missing,
                        "db_missing": db_missing,
                    })

    @staticmethod
    def _collect_consolidation(csv_rows, report):
        for row in csv_rows:
            if not row["consolidation"]:
                continue
            report["consolidation"].append({
                "lugar_id": row["lugar_id"],
                "nombre_lugar": row["nombre_lugar"],
                "comentarios": row["comentarios"],
            })

    # ------------------------------------------------------------- rendering

    def _render(self, report):
        w = self.stdout.write
        w(self.style.MIGRATE_HEADING("=" * 70))
        w(self.style.MIGRATE_HEADING("Lugar CSV ↔ database integrity audit"))
        w(self.style.MIGRATE_HEADING("=" * 70))
        w(f"CSV: {report['csv_path']}")

        t = report["totals"]
        w("")
        w(self.style.MIGRATE_LABEL("INPUT TOTALS"))
        w(f"  CSV rows parsed           : {t['csv_rows']}")
        w(f"  CSV rows unparseable      : {t['csv_unparseable_rows']}")
        w(f"  CSV duplicate lugar_ids   : {t['csv_duplicate_ids']}")
        w(f"  Database Lugar rows       : {t['db_rows']}")

        v = report["validation"]
        w("")
        w(self.style.MIGRATE_LABEL("1. VALIDATION OF EXISTING RECORDS"))
        w(f"  Matched (id + coordinates): {len(v['matched'])}")
        w(f"  Coordinate mismatches     : {len(v['coord_mismatch'])}")
        w(f"  Coord only in CSV         : {len(v['coord_mismatch_db_missing'])}")
        w(f"  Coord only in DB          : {len(v['coord_mismatch_csv_missing'])}")
        w(f"  Partial/unparseable coords: {len(v['coord_partial_in_csv'])}")
        w(f"  Name mismatches (info)    : {len(v['name_mismatch'])}")

        if v["coord_mismatch"]:
            w("")
            w(self.style.WARNING("  Coordinate mismatches detail:"))
            for e in v["coord_mismatch"]:
                w(
                    f"    #{e['lugar_id']} {e['nombre_lugar']}: "
                    f"csv=({e['csv_lat']}, {e['csv_lon']}) "
                    f"db=({e['db_lat']}, {e['db_lon']}) "
                    f"[{', '.join(e['mismatched_fields'])}]"
                )
        for section, label in (
            ("coord_mismatch_db_missing", "Coordinates only in CSV (DB null/partial)"),
            ("coord_mismatch_csv_missing", "Coordinates only in DB (CSV null/partial)"),
            ("coord_partial_in_csv", "Partial or unparseable coordinates"),
        ):
            if v[section]:
                w("")
                w(self.style.WARNING(f"  {label}:"))
                for e in v[section]:
                    w(
                        f"    #{e['lugar_id']} {e['nombre_lugar']}: "
                        f"csv=({e['csv_lat']}, {e['csv_lon']}) "
                        f"db=({e['db_lat']}, {e['db_lon']})"
                    )
        if v["name_mismatch"]:
            w("")
            w(self.style.WARNING("  Name mismatches (info):"))
            for e in v["name_mismatch"]:
                w(f"    #{e['lugar_id']}: csv={e['nombre_lugar']!r} db={e['db_nombre_lugar']!r}")

        w("")
        w(self.style.MIGRATE_LABEL("2. MISSING IN CSV (present in database)"))
        w(f"  Count: {len(report['missing_in_csv'])}")
        for e in report["missing_in_csv"]:
            w(f"    #{e['lugar_id']} {e['nombre_lugar']}")

        w("")
        w(self.style.MIGRATE_LABEL("3. MISSING IN DATABASE (present in CSV)"))
        w(f"  Count: {len(report['missing_in_db'])}")
        for e in report["missing_in_db"]:
            w(f"    #{e['lugar_id']} {e['nombre_lugar']}")

        mc = report["missing_coordinates"]
        w("")
        w(self.style.MIGRATE_LABEL("4. MISSING COORDINATES"))
        w(f"  CSV rows lacking lat/lon : {mc['csv']['total']}")
        w(f"    - unreferenceable (comment semantics): {len(mc['csv']['unreferenceable'])}")
        for e in mc["csv"]["unreferenceable"]:
            w(f"        #{e['lugar_id']} {e['nombre_lugar']} — {e['comentarios']}")
        w(f"    - plain missing data                 : {len(mc['csv']['plain'])}")
        w(f"  DB rows lacking lat/lon  : {mc['db']['total']}")
        w(f"    - unreferenceable (comment semantics): {len(mc['db']['unreferenceable'])}")
        w(f"    - plain missing data                 : {len(mc['db']['plain'])}")
        if mc["disagreements"]:
            w(self.style.WARNING(f"  Missingness disagreements CSV↔DB: {len(mc['disagreements'])}"))
            for e in mc["disagreements"][:10]:
                w(
                    f"    #{e['lugar_id']} {e['nombre_lugar']}: "
                    f"csv_missing={e['csv_missing']} db_missing={e['db_missing']}"
                )
            if len(mc["disagreements"]) > 10:
                w(f"    ... and {len(mc['disagreements']) - 10} more (see --report/--json)")

        w("")
        w(self.style.MIGRATE_LABEL("5. CONSOLIDATION HINTS (from comentarios)"))
        w(f"  Count: {len(report['consolidation'])}")
        for e in report["consolidation"]:
            w(f"    #{e['lugar_id']} {e['nombre_lugar']} — {e['comentarios']}")

        if report["parse_issues"]:
            w("")
            w(self.style.WARNING(f"PARSE ISSUES: {len(report['parse_issues'])}"))
            for e in report["parse_issues"]:
                w(f"    line {e['line']}: {e['reason']} (value: {e['value']!r})")
        if report["duplicate_ids"]:
            w("")
            w(self.style.WARNING(f"DUPLICATE IDS: {len(report['duplicate_ids'])}"))
            for e in report["duplicate_ids"]:
                w(f"    lugar_id {e['lugar_id']} repeated at line {e['line']}")

        w("")
        w(self.style.SUCCESS("Audit complete."))
