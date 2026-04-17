"""Cross-variable pivot-table endpoint for PersonaEsclavizada / PersonaNoEsclavizada.

Rows, columns and cells mirror the SlaveVoyages "table" view concept but adapted to
person-level data:  row dim × col dim → aggregated cell value (count / avg_edad / pct).
"""
import csv
import io
from collections import defaultdict

from django.db.models import Avg, Count, IntegerField, Min, OuterRef, Q, Subquery, Sum
from django.db.models.functions import ExtractYear
from django.http import StreamingHttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView

from dbgestor.models import PersonaEsclavizada, PersonaNoEsclavizada

# ── Dimension registry ────────────────────────────────────────────────────────
# Each entry describes a grouping axis available in the pivot table.
# Fields:
#   label       – Human-readable Spanish label shown in selects.
#   entities    – Which entity types support this dimension.
#   is_period   – Derives from Min(doc_year); Python merges years into intervals.
#   is_m2m      – True when the ORM path traverses a M2M relation.
#                 (totals can exceed unique-person count; UI shows a warning.)
#   values_field – ORM lookup path used in .values().
#   display_map – Optional DB-value → display-string mapping.
#   null_label  – Label for NULL/missing values.

DIMENSIONS = {
    'fecha_periodo': {
        'label': 'Período de tiempo',
        'entities': ['personaesclavizada', 'personanoesclavizada'],
        'is_period': True,
        'null_label': 'Desconocido',
    },
    'sexo': {
        'label': 'Sexo',
        'entities': ['personaesclavizada', 'personanoesclavizada'],
        'is_m2m': False,
        'values_field': 'sexo',
        'display_map': {'v': 'Varón', 'm': 'Mujer', 'i': 'Desconocido'},
        'null_label': 'Desconocido',
    },
    'etnonimos': {
        'label': 'Etnónimo',
        'entities': ['personaesclavizada'],
        'is_m2m': True,
        'values_field': 'etnonimos__etonimo',
        'null_label': 'Sin etnónimo',
    },
    'calidades': {
        'label': 'Calidad',
        'entities': ['personaesclavizada', 'personanoesclavizada'],
        'is_m2m': True,
        'values_field': 'calidades__calidad',
        'null_label': 'Sin calidad',
    },
    'hispanizacion': {
        'label': 'Hispanización',
        'entities': ['personaesclavizada'],
        'is_m2m': True,
        'values_field': 'hispanizacion__hispanizacion',
        'null_label': 'Sin información',
    },
    'procedencia': {
        'label': 'Procedencia (lugar)',
        'entities': ['personaesclavizada'],
        'is_m2m': False,
        'values_field': 'procedencia__nombre_lugar',
        'null_label': 'Sin procedencia',
    },
    'procedencia_region': {
        'label': 'Procedencia (región)',
        'entities': ['personaesclavizada'],
        'is_m2m': False,
        'values_field': 'procedencia__es_parte_de__nombre_lugar',
        'null_label': 'Sin región',
    },
    'estado_civil': {
        'label': 'Estado civil',
        'entities': ['personaesclavizada', 'personanoesclavizada'],
        'is_m2m': True,
        'values_field': 'estado_civil__estado_civil',
        'null_label': 'Sin información',
    },
    'lugar_nacimiento': {
        'label': 'Lugar de nacimiento',
        'entities': ['personaesclavizada', 'personanoesclavizada'],
        'is_m2m': False,
        'values_field': 'lugar_nacimiento__nombre_lugar',
        'null_label': 'Sin información',
    },
    'honorifico': {
        'label': 'Honorífico',
        'entities': ['personanoesclavizada'],
        'is_m2m': False,
        'values_field': 'honorifico',
        'display_map': {
            'nan': 'Sin honorífico', 'don': 'Don', 'dna': 'Doña',
            'doc': 'Doctor', 'fra': 'Fray',
        },
        'null_label': 'Desconocido',
    },
    'tipo_documental': {
        'label': 'Tipo documental',
        'entities': ['personaesclavizada', 'personanoesclavizada'],
        'is_m2m': True,
        'values_field': 'documentos__tipo_documento__tipo_documental',
        'null_label': 'Sin tipo',
    },
    'ocupaciones': {
        'label': 'Ocupación',
        'entities': ['personanoesclavizada'],
        'is_m2m': True,
        'values_field': 'ocupaciones__actividad',
        'null_label': 'Sin ocupación',
    },
}

CELL_OPS = {
    'count': {
        'label': 'Recuento de personas',
        'entities': ['personaesclavizada', 'personanoesclavizada'],
    },
    'avg_edad': {
        'label': 'Edad promedio',
        'entities': ['personaesclavizada'],
    },
    'pct_of_total': {
        'label': '% del total',
        'entities': ['personaesclavizada', 'personanoesclavizada'],
    },
}

_MODELS = {
    'personaesclavizada': PersonaEsclavizada,
    'personanoesclavizada': PersonaNoEsclavizada,
}


# ── Filter helpers ────────────────────────────────────────────────────────────

def _apply_form_filters(qs, type_key, request):
    """Mirrors SearchAPIView._apply_form_filters for standalone use."""
    p = request.query_params

    if type_key in ('personaesclavizada', 'personanoesclavizada'):
        if p.get('sexo'):
            qs = qs.filter(sexo=p['sexo'])
        if type_key == 'personanoesclavizada' and p.get('honorifico'):
            qs = qs.filter(honorifico=p['honorifico'])
        if p.get('calidades__calidad__icontains'):
            qs = qs.filter(
                calidades__calidad__icontains=p['calidades__calidad__icontains']
            ).distinct()
        if p.get('estado_civil'):
            qs = qs.filter(estado_civil__estado_civil=p['estado_civil']).distinct()
        if p.get('tipo_documental'):
            qs = qs.filter(
                documentos__tipo_documento__tipo_documental__icontains=p['tipo_documental']
            ).distinct()
        if p.get('archivo'):
            try:
                qs = qs.filter(documentos__archivo__archivo_id=int(p['archivo'])).distinct()
            except (ValueError, TypeError):
                pass
        if p.get('trayectoria_lugar'):
            lugar_ids = [
                int(x) for x in p['trayectoria_lugar'].split(',')
                if x.strip().isdigit()
            ]
            for lid in lugar_ids:
                qs = qs.filter(p_x_l_pere__lugar__lugar_id=lid)
            if lugar_ids:
                qs = qs.distinct()

        for shared_key in ('fecha_documento__gte', 'fecha_documento__lte'):
            val = p.get(shared_key)
            if val:
                if len(val) == 4 and val.isdigit():
                    val = f"{val}-01-01" if 'gte' in shared_key else f"{val}-12-31"
                lookup = (
                    'documentos__fecha_inicial__gte' if 'gte' in shared_key
                    else 'documentos__fecha_inicial__lte'
                )
                qs = qs.filter(**{lookup: val}).distinct()

        if type_key == 'personanoesclavizada':
            if p.get('ocupaciones__actividad__icontains'):
                qs = qs.filter(
                    ocupaciones__actividad__icontains=p['ocupaciones__actividad__icontains']
                ).distinct()

        if type_key == 'personaesclavizada':
            if p.get('edad__gte'):
                try:
                    qs = qs.filter(edad__gte=int(p['edad__gte']))
                except (ValueError, TypeError):
                    pass
            if p.get('edad__lte'):
                try:
                    qs = qs.filter(edad__lte=int(p['edad__lte']))
                except (ValueError, TypeError):
                    pass
            if p.get('etnonimos__etonimo__icontains'):
                qs = qs.filter(
                    etnonimos__etonimo__icontains=p['etnonimos__etonimo__icontains']
                ).distinct()
            if p.get('hispanizacion__hispanizacion__icontains'):
                qs = qs.filter(
                    hispanizacion__hispanizacion__icontains=p['hispanizacion__hispanizacion__icontains']
                ).distinct()
            if p.get('procedencia'):
                try:
                    qs = qs.filter(procedencia__lugar_id=int(p['procedencia']))
                except (ValueError, TypeError):
                    pass
            for fld in ('altura', 'cabello', 'ojos', 'marcas_corporales', 'conducta', 'salud'):
                val = p.get(f'{fld}__icontains')
                if val:
                    qs = qs.filter(**{f'{fld}__icontains': val})

    return qs


def _apply_sidebar_filters(qs, type_key, request):
    """Apply sidebar facet filters (lugar_id, archivo_id, year, etnonimo, etc.)."""
    p = request.query_params

    def _csv_ints(key):
        return [int(x) for x in p.get(key, '').split(',') if x.strip().isdigit()]

    def _csv_strs(key):
        return [x.strip() for x in p.get(key, '').split(',') if x.strip()]

    lugar_ids = _csv_ints('lugar_id')
    if lugar_ids:
        qs = qs.filter(p_x_l_pere__lugar__lugar_id__in=lugar_ids).distinct()

    archivo_ids = _csv_ints('archivo_id')
    if archivo_ids:
        qs = qs.filter(documentos__archivo__archivo_id__in=archivo_ids).distinct()

    years = _csv_ints('year')
    if years:
        qs = qs.filter(documentos__fecha_inicial__year__in=years).distinct()

    if type_key == 'personaesclavizada':
        etnonimos = _csv_strs('etnonimo')
        if etnonimos:
            qs = qs.filter(etnonimos__etonimo__in=etnonimos).distinct()
        calidades = _csv_strs('calidad')
        if calidades:
            qs = qs.filter(calidades__calidad__in=calidades).distinct()
        hispanizaciones = _csv_strs('hispanizacion')
        if hispanizaciones:
            qs = qs.filter(hispanizacion__hispanizacion__in=hispanizaciones).distinct()
        ocupaciones = _csv_strs('ocupacion')
        if ocupaciones:
            qs = qs.filter(ocupaciones__actividad__in=ocupaciones).distinct()

    return qs


# ── Pivot helpers ─────────────────────────────────────────────────────────────

def _period_label(year, size):
    """1783 + size=50  →  '1750–1799'."""
    if year is None:
        return None
    start = (year // size) * size
    return f"{start}–{start + size - 1}"


def _to_display(val, conf):
    """Map a raw DB value to its display string using the dimension's display_map."""
    if val is None:
        return None
    dm = conf.get('display_map')
    if dm:
        return dm.get(val, str(val))
    return str(val)


def _build_pivot(raw_qs, row_conf, col_conf, row_vf, col_vf, period_size, cell_op):
    """
    Consume the annotated queryset and build the pivot matrix.

    Returns (matrix, sorted_row_keys, sorted_col_keys) where:
        matrix[row_key][col_key] = {'count': int, 'sum_edad': int, 'n_edad': int}
    """
    matrix = defaultdict(lambda: defaultdict(lambda: {'count': 0, 'sum_edad': 0, 'n_edad': 0}))

    for row in raw_qs:
        r_raw = row[row_vf]
        c_raw = row[col_vf]

        # Convert raw value to grouping key
        if row_conf.get('is_period'):
            r_key = (r_raw // period_size) * period_size if r_raw is not None else None
        else:
            r_key = _to_display(r_raw, row_conf)
            if r_key is None:
                r_key = None  # explicit null bucket

        if col_conf.get('is_period'):
            c_key = (c_raw // period_size) * period_size if c_raw is not None else None
        else:
            c_key = _to_display(c_raw, col_conf)
            if c_key is None:
                c_key = None

        cell = matrix[r_key][c_key]
        cell['count'] += row['_count']
        cell['sum_edad'] += row.get('_sum_edad') or 0
        cell['n_edad'] += row.get('_n_edad') or 0

    def _row_total(rk):
        return sum(c['count'] for c in matrix[rk].values())

    def _col_total(ck):
        return sum(matrix[rk].get(ck, {}).get('count', 0) for rk in matrix)

    all_row_keys = list(matrix.keys())
    all_col_keys = list({ck for rv in matrix.values() for ck in rv})

    def _sort_row(k):
        if k is None:
            return (1, 0, '')
        if row_conf.get('is_period'):
            return (0, k, '')
        return (0, -_row_total(k), str(k))

    def _sort_col(k):
        if k is None:
            return (1, 0, '')
        if col_conf.get('is_period'):
            return (0, k, '')
        return (0, -_col_total(k), str(k))

    sorted_row_keys = sorted(all_row_keys, key=_sort_row)
    sorted_col_keys = sorted(all_col_keys, key=_sort_col)

    return matrix, sorted_row_keys, sorted_col_keys


def _label_for_key(key, conf, period_size):
    if key is None:
        return conf['null_label']
    if conf.get('is_period'):
        return _period_label(key, period_size)
    return str(key)


def _cell_value(cell, grand_count, cell_op):
    count = cell.get('count', 0)
    result = {'count': count}
    if cell_op in ('count', 'pct_of_total'):
        result['pct'] = round(count / grand_count * 100, 1) if grand_count > 0 else 0
    if cell_op == 'avg_edad':
        n = cell.get('n_edad', 0)
        s = cell.get('sum_edad', 0)
        result['avg_edad'] = round(s / n, 1) if n > 0 else None
    return result


def _total_value(merged_cells, grand_count, cell_op):
    total_count = sum(c.get('count', 0) for c in merged_cells)
    result = {'count': total_count}
    if cell_op in ('count', 'pct_of_total'):
        result['pct'] = round(total_count / grand_count * 100, 1) if grand_count > 0 else 0
    if cell_op == 'avg_edad':
        total_n = sum(c.get('n_edad', 0) for c in merged_cells)
        total_s = sum(c.get('sum_edad', 0) for c in merged_cells)
        result['avg_edad'] = round(total_s / total_n, 1) if total_n > 0 else None
    return result


# ── View ──────────────────────────────────────────────────────────────────────

class CrosstabView(APIView):
    """
    GET /api/v2/crosstab/

    Query params:
        type          personaesclavizada | personanoesclavizada
        row_dim       dimension key from DIMENSIONS
        col_dim       dimension key from DIMENSIONS (must differ from row_dim)
        period_size   25 | 50 | 100  (only relevant when a dim is fecha_periodo)
        cell_op       count | avg_edad | pct_of_total
        format        json (default) | csv
        + all standard search/filter params accepted by SearchAPIView
    """

    def get(self, request):  # noqa: C901
        p = request.query_params
        entity_type = p.get('type', 'personaesclavizada')
        row_dim = p.get('row_dim', '')
        col_dim = p.get('col_dim', '')
        cell_op = p.get('cell_op', 'count')
        fmt = p.get('format', 'json')

        try:
            period_size = int(p.get('period_size', 50))
            if period_size not in (25, 50, 100):
                period_size = 50
        except (ValueError, TypeError):
            period_size = 50

        # ── Validation ────────────────────────────────────────────────────────
        if entity_type not in _MODELS:
            return Response(
                {'error': 'type must be personaesclavizada or personanoesclavizada'},
                status=400,
            )

        if not row_dim or row_dim not in DIMENSIONS:
            return Response(
                {'error': f'row_dim invalid. Options: {list(DIMENSIONS)}'},
                status=400,
            )

        if not col_dim or col_dim not in DIMENSIONS:
            return Response(
                {'error': f'col_dim invalid. Options: {list(DIMENSIONS)}'},
                status=400,
            )

        if row_dim == col_dim:
            return Response({'error': 'row_dim and col_dim must differ'}, status=400)

        row_conf = DIMENSIONS[row_dim]
        col_conf = DIMENSIONS[col_dim]

        if entity_type not in row_conf['entities']:
            return Response(
                {'error': f"'{row_dim}' is not available for {entity_type}"},
                status=400,
            )

        if entity_type not in col_conf['entities']:
            return Response(
                {'error': f"'{col_dim}' is not available for {entity_type}"},
                status=400,
            )

        if row_conf.get('is_period') and col_conf.get('is_period'):
            return Response(
                {'error': 'Row and column cannot both be time-period dimensions'},
                status=400,
            )

        if cell_op not in CELL_OPS:
            cell_op = 'count'

        if cell_op == 'avg_edad' and entity_type != 'personaesclavizada':
            return Response(
                {'error': 'avg_edad is only available for personaesclavizada'},
                status=400,
            )

        # ── Build queryset ────────────────────────────────────────────────────
        model = _MODELS[entity_type]
        qs = model.objects.all()
        qs = _apply_sidebar_filters(qs, entity_type, request)
        qs = _apply_form_filters(qs, entity_type, request)

        # ── Annotate period dims with min document year ───────────────────────
        # Use a correlated Subquery so the min-year is a per-row scalar.
        # A plain Min(ExtractYear(...)) is an aggregate that gets collapsed
        # by the subsequent .values().annotate() GROUP BY, producing wrong
        # results (one row per sexo instead of one per sexo × year).
        if row_conf.get('is_period') or col_conf.get('is_period'):
            _year_sq = Subquery(
                model.objects.filter(pk=OuterRef('pk')).annotate(
                    _yr=Min(ExtractYear('documentos__fecha_inicial'))
                ).values('_yr'),
                output_field=IntegerField(),
            )

        if row_conf.get('is_period'):
            qs = qs.annotate(_row_year=_year_sq)
            row_vf = '_row_year'
        else:
            row_vf = row_conf['values_field']

        if col_conf.get('is_period'):
            qs = qs.annotate(_col_year=_year_sq)
            col_vf = '_col_year'
        else:
            col_vf = col_conf['values_field']

        # ── Aggregation ───────────────────────────────────────────────────────
        anno = {'_count': Count('persona_id', distinct=True)}
        if cell_op == 'avg_edad':
            anno['_sum_edad'] = Sum('edad')
            anno['_n_edad'] = Count('edad')  # non-null edad entries

        raw_qs = qs.values(row_vf, col_vf).annotate(**anno)

        # ── Build pivot matrix ────────────────────────────────────────────────
        matrix, sorted_row_keys, sorted_col_keys = _build_pivot(
            raw_qs, row_conf, col_conf, row_vf, col_vf, period_size, cell_op
        )

        rows = [_label_for_key(k, row_conf, period_size) for k in sorted_row_keys]
        cols = [_label_for_key(k, col_conf, period_size) for k in sorted_col_keys]

        grand_count = sum(
            matrix[rk][ck]['count']
            for rk in sorted_row_keys for ck in matrix[rk]
        )

        cells = [
            [
                _cell_value(matrix[rk].get(ck, {}), grand_count, cell_op)
                for ck in sorted_col_keys
            ]
            for rk in sorted_row_keys
        ]

        row_totals = [
            _total_value(list(matrix[rk].values()), grand_count, cell_op)
            for rk in sorted_row_keys
        ]

        col_totals = [
            _total_value(
                [matrix[rk].get(ck, {}) for rk in sorted_row_keys],
                grand_count,
                cell_op,
            )
            for ck in sorted_col_keys
        ]

        grand_all_cells = [matrix[rk][ck] for rk in sorted_row_keys for ck in matrix[rk]]
        grand_total = _total_value(grand_all_cells, grand_count, cell_op)

        is_m2m = row_conf.get('is_m2m', False) or col_conf.get('is_m2m', False)

        payload = {
            'rows': rows,
            'cols': cols,
            'cells': cells,
            'row_totals': row_totals,
            'col_totals': col_totals,
            'grand_total': grand_total,
            'meta': {
                'entity_type': entity_type,
                'row_dim': row_dim,
                'row_dim_label': row_conf['label'],
                'col_dim': col_dim,
                'col_dim_label': col_conf['label'],
                'cell_op': cell_op,
                'cell_op_label': CELL_OPS[cell_op]['label'],
                'period_size': (
                    period_size
                    if row_conf.get('is_period') or col_conf.get('is_period')
                    else None
                ),
                'is_m2m': is_m2m,
                'm2m_warning': (
                    'Una o ambas dimensiones son relaciones múltiples (M2M). '
                    'Los totales de fila/columna pueden superar el recuento total de '
                    'personas porque una misma persona puede aparecer en varias celdas.'
                ) if is_m2m else None,
                'total_personas': grand_count,
            },
        }

        if fmt == 'csv':
            return _render_csv(payload, row_conf['label'], col_conf['label'], cell_op)

        return Response(payload)


def _render_csv(data, row_label, col_label, cell_op):
    """Stream the pivot matrix as a CSV attachment."""
    def _cell_str(cell):
        if cell_op == 'avg_edad':
            v = cell.get('avg_edad')
            return '' if v is None else str(v)
        if cell_op == 'pct_of_total':
            return str(cell.get('pct', 0))
        return str(cell.get('count', 0))

    def _stream():
        buf = io.StringIO()
        writer = csv.writer(buf)

        # Header: row-dim label | col values | Total
        writer.writerow([row_label] + data['cols'] + ['Total'])
        yield buf.getvalue()
        buf.truncate(0)
        buf.seek(0)

        for i, row_name in enumerate(data['rows']):
            row = [row_name] + [_cell_str(c) for c in data['cells'][i]]
            row.append(_cell_str(data['row_totals'][i]))
            writer.writerow(row)
            yield buf.getvalue()
            buf.truncate(0)
            buf.seek(0)

        # Totals footer
        footer = ['Total'] + [_cell_str(c) for c in data['col_totals']]
        footer.append(_cell_str(data['grand_total']))
        writer.writerow(footer)
        yield buf.getvalue()

    response = StreamingHttpResponse(_stream(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="crosstab.csv"'
    return response


# ── Schema endpoint ───────────────────────────────────────────────────────────

class CrosstabSchemaView(APIView):
    """Return available dimensions and cell operations (for the frontend selects)."""

    def get(self, request):
        entity_type = request.query_params.get('type', '')
        dims = {
            k: {
                'label': v['label'],
                'is_period': v.get('is_period', False),
                'is_m2m': v.get('is_m2m', False),
                'entities': v['entities'],
            }
            for k, v in DIMENSIONS.items()
            if not entity_type or entity_type in v['entities']
        }
        ops = {
            k: {
                'label': v['label'],
                'entities': v['entities'],
            }
            for k, v in CELL_OPS.items()
            if not entity_type or entity_type in v['entities']
        }
        return Response({'dimensions': dims, 'cell_ops': ops})
