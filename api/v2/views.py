import json
import logging
import re
from collections import defaultdict

from django.db.models import Count, F, Q, Prefetch, Min, Max
from django.db.models.functions import ExtractYear
from django.contrib.auth import authenticate, login, logout
from django.contrib.postgres.search import SearchQuery, SearchRank, TrigramSimilarity
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponse
from django.middleware.csrf import get_token
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from urllib.parse import urlencode
from rest_framework.pagination import PageNumberPagination
import csv

from dbgestor.models import (Archivo, Documento, PersonaEsclavizada, PersonaNoEsclavizada, Corporacion,
                             PersonaLugarRel, Lugar, PersonaRelaciones, Persona,
                             PersonaRolEvento, InstitucionRolEvento,
                             Calidades, Hispanizaciones, Etonimos, EstadoCivil,
                             Actividades as ActividadesModel, SituacionLugar, TipoDocumental,
                             RolEvento, TiposInstitucion)

from .serializers import (
    # Reference serializers
    ArchivoReferenceSerializer, DocumentoReferenceSerializer, PersonaReferenceSerializer,
    LugarReferenceSerializer, CorporacionReferenceSerializer,

    # List serializers
    ArchivoListSerializer, DocumentoListSerializer, PersonaListSerializer,
    PersonaEsclavizadaListSerializer, PersonaNoEsclavizadaListSerializer,
    LugarListSerializer, CorporacionListSerializer,

    # Detail serializers
    ArchivoDetailSerializer, DocumentoDetailSerializer, PersonaDetailSerializer,
    PersonaEsclavizadaDetailSerializer, PersonaNoEsclavizadaDetailSerializer,
    LugarDetailSerializer, CorporacionDetailSerializer,
    LugarPersonasRelSerializer,

    # Relationship serializers
    PersonaRelacionesDetailSerializer, PersonaLugarRelDetailSerializer,
    PersonaRolEventoDetailSerializer, ActividadesSerializer, LogMessageSerializer,

    # Travel trajectory serializers
    TravelTrajectorySerializer, PersonaTravelTrajectorySerializer,

    # History serializers
    DocumentoHistorySerializer, PersonaHistorySerializer, CorporacionHistorySerializer,

    # Write serializers
    ArchivoWriteSerializer, LugarWriteSerializer, DocumentoWriteSerializer,
    PersonaEsclavizadaWriteSerializer, PersonaNoEsclavizadaWriteSerializer,
    CorporacionWriteSerializer,
    PersonaLugarRelWriteSerializer, PersonaRelacionesWriteSerializer,
    PersonaRolEventoWriteSerializer, InstitucionRolEventoWriteSerializer,
    TipoDocumentalWriteSerializer, CalidadesWriteSerializer, HispanizacionesWriteSerializer,
    EtnonimosWriteSerializer, EstadoCivilWriteSerializer, ActividadesWriteSerializer,
    SituacionLugarWriteSerializer, RolEventoWriteSerializer, TiposInstitucionWriteSerializer,
)


logger = logging.getLogger('dbgestor')


def parse_search_query(raw_query):
    """Detect quoted queries and return (clean_query, is_exact).
    Quoted input (single or double) triggers phrase search with no fuzzy fallback."""
    match = re.fullmatch(r'["\'](.+)["\']', raw_query.strip())
    if match:
        return match.group(1), True
    return raw_query, False


class APIPerm(BasePermission):
    """
    Custom permission for API access.
    """
    def has_permission(self, request, view):
        return True  # Adjust based on your authentication requirements


class CustomPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class BrowsePagination(PageNumberPagination):
    """Pagination for browse/table views — allows larger page sizes."""
    page_size = 30
    page_size_query_param = 'page_size'
    max_page_size = 300


class DocumentoLinkMixin:
    """Adds vincular/desvincular @actions so the cataloguer hub can manage
    the Persona/Corporacion ↔ Documento M2M without a full PATCH."""

    @action(detail=True, methods=['post'], url_path='vincular')
    def vincular(self, request, **kwargs):
        obj = self.get_object()
        doc_id = request.data.get('documento_id')
        if not doc_id:
            return Response({'error': 'documento_id requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        obj.documentos.add(doc_id)
        return Response({'status': 'vinculado'})

    @action(detail=True, methods=['post'], url_path='desvincular')
    def desvincular(self, request, **kwargs):
        obj = self.get_object()
        doc_id = request.data.get('documento_id')
        if not doc_id:
            return Response({'error': 'documento_id requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        obj.documentos.remove(doc_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


# Base ViewSet with common functionality
class BaseV2ViewSet(viewsets.ModelViewSet):
    permission_classes = [APIPerm]
    pagination_class = CustomPagination

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy',
                           'bulk_update_ordinal', 'vincular', 'desvincular'):
            return [IsAuthenticated()]
        return super().get_permissions()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = []
    search_fields = []
    ordering_fields = []
    ordering = ['-created_at']

    def get_pagination_class(self):
        """Use BrowsePagination when client requests page_size > 100."""
        page_size = self.request.query_params.get('page_size')
        if page_size and int(page_size) > 100:
            return BrowsePagination
        return self.pagination_class

    @property
    def paginator(self):
        if not hasattr(self, '_paginator'):
            pagination_class = self.get_pagination_class()
            if pagination_class is None:
                self._paginator = None
            else:
                self._paginator = pagination_class()
        return self._paginator

    def get_serializer_class(self):
        """
        Return different serializers for list vs detail vs write actions.
        """
        if self.action in ('create', 'update', 'partial_update'):
            return getattr(self, 'write_serializer_class', self.serializer_class)
        if self.action == 'list':
            return getattr(self, 'list_serializer_class', self.serializer_class)
        if self.action == 'retrieve':
            return getattr(self, 'detail_serializer_class', self.serializer_class)
        return self.serializer_class

    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        """
        Export data as CSV - using list serializer for lightweight export
        """
        queryset = self.filter_queryset(self.get_queryset())[:1000]  # Limit to prevent timeout
        serializer_class = getattr(self, 'list_serializer_class', self.serializer_class)
        serializer = serializer_class(queryset, many=True)
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{self.get_export_filename()}"'
        
        if serializer.data:
            writer = csv.DictWriter(response, fieldnames=serializer.data[0].keys())
            writer.writeheader()
            for row in serializer.data:
                # Flatten any nested objects for CSV
                flattened_row = self.flatten_for_csv(row)
                writer.writerow(flattened_row)
        
        return response

    def get_export_filename(self):
        """Override in subclasses to provide meaningful filenames"""
        return f"{self.__class__.__name__.lower().replace('viewset', '')}_export.csv"

    def flatten_for_csv(self, row):
        """Flatten nested objects for CSV export"""
        flattened = {}
        for key, value in row.items():
            if isinstance(value, dict):
                # For nested objects, include just the ID and name/title
                if 'id' in value:
                    flattened[f"{key}_id"] = value.get('id')
                if 'nombre' in value:
                    flattened[f"{key}_nombre"] = value.get('nombre')
                elif 'titulo' in value:
                    flattened[f"{key}_titulo"] = value.get('titulo')
                elif 'nombre_lugar' in value:
                    flattened[f"{key}_nombre"] = value.get('nombre_lugar')
            elif isinstance(value, list):
                # For lists, join IDs or convert to string
                if value and isinstance(value[0], dict):
                    ids = [str(item.get('id', '')) for item in value if 'id' in item]
                    flattened[f"{key}_ids"] = '; '.join(ids)
                else:
                    flattened[key] = '; '.join([str(v) for v in value])
            else:
                flattened[key] = value
        return flattened


# Archivo ViewSet
class ArchivoViewSet(BaseV2ViewSet):
    queryset = Archivo.objects.all()
    serializer_class = ArchivoListSerializer
    list_serializer_class = ArchivoListSerializer
    detail_serializer_class = ArchivoDetailSerializer
    write_serializer_class = ArchivoWriteSerializer
    lookup_field = 'archivo_id'

    def get_export_filename(self):
        return "archivos_export.csv"

    @action(detail=True, methods=['get'])
    def documentos(self, request, archivo_id=None):
        """Get all documents for this archivo"""
        archivo = self.get_object()
        documentos = archivo.documento_set.all()
        page = self.paginate_queryset(documentos)
        
        if page is not None:
            serializer = DocumentoListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = DocumentoListSerializer(documentos, many=True)
        return Response(serializer.data)


# Documento ViewSet
class DocumentoViewSet(BaseV2ViewSet):
    queryset = Documento.objects.select_related('archivo', 'lugar_de_produccion').all()
    serializer_class = DocumentoListSerializer
    list_serializer_class = DocumentoListSerializer
    detail_serializer_class = DocumentoDetailSerializer
    write_serializer_class = DocumentoWriteSerializer
    lookup_field = 'documento_id'
    filterset_fields = {
        'archivo__archivo_id': ['exact'],
        'tipo_documento__tipo_documental': ['exact', 'icontains'],
        'lugar_de_produccion__lugar_id': ['exact'],
        'fecha_inicial': ['exact', 'gte', 'lte'],
        'fecha_final': ['exact', 'gte', 'lte'],
    }
    search_fields = ['titulo', 'descripcion', 'documento_idno']
    ordering_fields = ['titulo', 'fecha_inicial', 'fecha_final', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def get_export_filename(self):
        return "documentos_export.csv"

    @action(detail=False, methods=['get'])
    def search(self, request):
        """PostgreSQL full-text and trigram search. Wrap query in quotes for exact match."""
        raw_query = request.query_params.get('q', '')
        if not raw_query:
            return Response({'error': 'No query provided'}, status=400)

        try:
            query, is_exact = parse_search_query(raw_query)
            search_type = 'phrase' if is_exact else 'plain'
            search_query = SearchQuery(query, config='spanish', search_type=search_type)

            queryset = Documento.objects.annotate(
                search_rank=SearchRank(F('search_vector'), search_query),
                titulo_similarity=TrigramSimilarity('titulo', query),
                descripcion_similarity=TrigramSimilarity('descripcion', query)
            )

            if is_exact:
                queryset = queryset.filter(search_vector=search_query)
            else:
                queryset = queryset.filter(
                    Q(search_vector=search_query) |
                    Q(titulo_similarity__gt=0.3) |
                    Q(descripcion_similarity__gt=0.3)
                )

            queryset = queryset.filter(
                is_published=True
            ).order_by(
                '-search_rank',
                '-titulo_similarity',
                '-updated_at'
            ).distinct()
            
            page = self.paginate_queryset(queryset)
            
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error executing search: {str(e)}")
            return Response({'error': 'An error occurred during the search'}, status=500)

    @action(detail=True, methods=['get'])
    def personas(self, request, documento_id=None):
        """Get all personas for this documento"""
        documento = self.get_object()
        personas = documento.persona_set.all()
        page = self.paginate_queryset(personas)
        
        if page is not None:
            serializer = PersonaListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = PersonaListSerializer(personas, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def history(self, request, documento_id=None):
        """Get change history for this documento"""
        documento = self.get_object()
        history_records = documento.history.all().order_by('-history_date')
        
        page = self.paginate_queryset(history_records)
        if page is not None:
            serializer = DocumentoHistorySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = DocumentoHistorySerializer(history_records, many=True)
        return Response(serializer.data)


# Persona ViewSets
class PersonaEsclavizadaViewSet(DocumentoLinkMixin, BaseV2ViewSet):
    queryset = PersonaEsclavizada.objects.prefetch_related('documentos', 'ocupaciones').all()
    serializer_class = PersonaEsclavizadaListSerializer
    list_serializer_class = PersonaEsclavizadaListSerializer
    detail_serializer_class = PersonaEsclavizadaDetailSerializer
    write_serializer_class = PersonaEsclavizadaWriteSerializer
    lookup_field = 'persona_id'
    filterset_fields = {
        'sexo': ['exact'],
        'edad': ['exact', 'gte', 'lte'],
        'hispanizacion__hispanizacion': ['exact', 'icontains'],
        'etnonimos__etonimo': ['exact', 'icontains'],
        'calidades__calidad': ['exact', 'icontains'],
        'ocupaciones__actividad': ['exact', 'icontains'],
        'documentos__documento_id': ['exact'],
    }
    search_fields = ['nombre_normalizado', 'nombres', 'apellidos', 'persona_idno']
    ordering_fields = ['nombre_normalizado', 'edad', 'created_at', 'updated_at', 'fecha_nacimiento', 'earliest_doc_date', 'latest_doc_date']
    ordering = ['-created_at']

    def get_export_filename(self):
        return "personas_esclavizadas_export.csv"

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.action == 'list':
            queryset = queryset.prefetch_related(
                'etnonimos', 'hispanizacion', 'calidades', 'relaciones', 'p_x_l_pere',
            ).annotate(
                earliest_doc_date=Min('documentos__fecha_inicial'),
                latest_doc_date=Max('documentos__fecha_inicial'),
            )
        elif self.action in ('retrieve', 'trajectory'):
            queryset = queryset.select_related(
                'procedencia', 'lugar_nacimiento', 'lugar_defuncion',
            ).prefetch_related(
                'documentos__archivo',
                'relaciones__personas',
                Prefetch('p_x_l_pere',
                         queryset=PersonaLugarRel.objects.select_related(
                             'lugar', 'situacion_lugar', 'documento'
                         ).order_by('ordinal')),
            )
        
        return queryset

    @action(detail=False, methods=['get'])
    def search(self, request):
        """PostgreSQL full-text and trigram search for enslaved persons. Quotes for exact match."""
        raw_query = request.query_params.get('q', '')
        if not raw_query:
            return Response({'error': 'No query provided'}, status=400)

        try:
            query, is_exact = parse_search_query(raw_query)
            search_type = 'phrase' if is_exact else 'plain'
            search_query = SearchQuery(query, config='spanish', search_type=search_type)

            queryset = PersonaEsclavizada.objects.annotate(
                search_rank=SearchRank(F('search_vector'), search_query),
                nombre_similarity=TrigramSimilarity('nombre_normalizado', query),
                nombres_similarity=TrigramSimilarity('nombres', query)
            )

            if is_exact:
                queryset = queryset.filter(search_vector=search_query)
            else:
                queryset = queryset.filter(
                    Q(search_vector=search_query) |
                    Q(nombre_similarity__gt=0.3) |
                    Q(nombres_similarity__gt=0.3)
                )

            queryset = queryset.filter(
                is_published=True
            ).order_by(
                '-search_rank',
                '-nombre_similarity',
                '-updated_at'
            ).distinct()
            
            page = self.paginate_queryset(queryset)
            
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error executing search: {str(e)}")
            return Response({'error': 'An error occurred during the search'}, status=500)

    @action(detail=True, methods=['get'])
    def relaciones(self, request, persona_id=None):
        """Get all relationships for this persona"""
        persona = self.get_object()
        relaciones = persona.relaciones.all()
        page = self.paginate_queryset(relaciones)
        
        if page is not None:
            serializer = PersonaRelacionesDetailSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = PersonaRelacionesDetailSerializer(relaciones, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def lugares(self, request, persona_id=None):
        """Get all place relationships for this persona"""
        persona = self.get_object()
        lugares_rel = persona.p_x_l_pere.all()
        page = self.paginate_queryset(lugares_rel)
        
        if page is not None:
            serializer = PersonaLugarRelDetailSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = PersonaLugarRelDetailSerializer(lugares_rel, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def network(self, request, persona_id=None):
        """
        Build a Cytoscape-ready ego-network graph for this persona.
        Returns {nodes, edges} filtered to people connected via shared relaciones.
        """
        persona = self.get_object()
        relaciones = persona.relaciones.prefetch_related('personas').all()

        # Collect every persona that shares a relacion with the current one
        node_map = {}
        edges = []

        for rel in relaciones:
            rel_personas = list(rel.personas.all())
            persona_ids_in_rel = [p.persona_id for p in rel_personas]

            for p in rel_personas:
                if p.persona_id not in node_map:
                    node_map[p.persona_id] = {
                        'data': {
                            'id': f'p{p.persona_id}',
                            'label': p.nombre_normalizado or str(p.persona_id),
                            'type': p.polymorphic_ctype_id,
                        }
                    }

            # Create edges between all pairs in this relacion
            nat = rel.naturaleza_relacion or ''
            rel_type = 'fam' if 'fam' in nat.lower() else (
                        'aso' if 'aso' in nat.lower() else 'tmp')
            for i, pid_a in enumerate(persona_ids_in_rel):
                for pid_b in persona_ids_in_rel[i + 1:]:
                    edges.append({
                        'data': {
                            'source': f'p{pid_a}',
                            'target': f'p{pid_b}',
                            'relation': rel_type,
                            'label': rel.descripcion_relacion or nat,
                        }
                    })

        return Response({
            'nodes': list(node_map.values()),
            'edges': edges,
        })

    @action(detail=True, methods=['get'])
    def trajectory(self, request, persona_id=None):
        """
        Return ordered trajectory arcs for map visualization.
        Each arc has from/to coordinates and a date.
        Includes direct FK places: lugar_nacimiento, procedencia, lugar_defuncion.
        """
        persona = self.get_object()
        places = (persona.p_x_l_pere
                  .select_related('lugar', 'documento')
                  .order_by('ordinal'))

        # Collect persona_x_lugares points
        rel_points = []
        for rel in places:
            lugar = rel.lugar
            if lugar and lugar.lat and lugar.lon:
                rel_points.append({
                    'nombre': lugar.nombre_lugar,
                    'lat': float(lugar.lat),
                    'lon': float(lugar.lon),
                    'fecha': (rel.fecha_inicial_lugar
                              or (rel.documento.fecha_inicial if rel.documento else None)),
                    'ordinal': rel.ordinal,
                    'situacion': str(rel.situacion_lugar) if rel.situacion_lugar else None,
                })

        # Determine ordinal bounds for FK places
        min_ordinal = min((p['ordinal'] for p in rel_points), default=1)
        max_ordinal = max((p['ordinal'] for p in rel_points), default=0)

        # Inject direct FK places (nacimiento, procedencia, defuncion)
        fk_points = []
        seen_lugar_ids = set()

        # lugar_nacimiento → before everything
        nac = getattr(persona, 'lugar_nacimiento', None)
        if nac and nac.lat and nac.lon:
            fk_points.append({
                'nombre': nac.nombre_lugar,
                'lat': float(nac.lat),
                'lon': float(nac.lon),
                'fecha': None,
                'ordinal': min_ordinal - 2,
                'situacion': 'Nacimiento',
            })
            seen_lugar_ids.add(nac.lugar_id)

        # procedencia → origin, right before existing trajectory
        proc = getattr(persona, 'procedencia', None)
        if proc and proc.lat and proc.lon and proc.lugar_id not in seen_lugar_ids:
            fk_points.append({
                'nombre': proc.nombre_lugar,
                'lat': float(proc.lat),
                'lon': float(proc.lon),
                'fecha': None,
                'ordinal': min_ordinal - 1,
                'situacion': 'Procedencia',
            })

        # lugar_defuncion → after everything
        defn = getattr(persona, 'lugar_defuncion', None)
        if defn and defn.lat and defn.lon:
            fk_points.append({
                'nombre': defn.nombre_lugar,
                'lat': float(defn.lat),
                'lon': float(defn.lon),
                'fecha': None,
                'ordinal': max_ordinal + 1,
                'situacion': 'Defunción',
            })

        # Merge and sort all points by ordinal
        points = sorted(fk_points + rel_points, key=lambda p: p['ordinal'])

        # Build arcs between consecutive points
        arcs = []
        for i in range(len(points) - 1):
            arcs.append({
                'from': {
                    'name': points[i]['nombre'],
                    'lat': points[i]['lat'],
                    'lon': points[i]['lon'],
                    'situacion': points[i].get('situacion'),
                },
                'to': {
                    'name': points[i + 1]['nombre'],
                    'lat': points[i + 1]['lat'],
                    'lon': points[i + 1]['lon'],
                    'situacion': points[i + 1].get('situacion'),
                },
                'date': str(points[i]['fecha'] or ''),
            })

        return Response(arcs)

    @action(detail=True, methods=['get'])
    def history(self, request, persona_id=None):
        """Get change history for this persona"""
        persona = self.get_object()
        history_records = persona.history.all().order_by('-history_date')
        
        page = self.paginate_queryset(history_records)
        if page is not None:
            serializer = PersonaHistorySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = PersonaHistorySerializer(history_records, many=True)
        return Response(serializer.data)


class PersonaNoEsclavizadaViewSet(DocumentoLinkMixin, BaseV2ViewSet):
    queryset = PersonaNoEsclavizada.objects.prefetch_related('documentos').all()
    serializer_class = PersonaNoEsclavizadaListSerializer
    list_serializer_class = PersonaNoEsclavizadaListSerializer
    detail_serializer_class = PersonaNoEsclavizadaDetailSerializer
    write_serializer_class = PersonaNoEsclavizadaWriteSerializer
    lookup_field = 'persona_id'
    filterset_fields = {
        'sexo': ['exact'],
        'honorifico': ['exact'],
        'documentos__documento_id': ['exact'],
    }
    search_fields = ['nombre_normalizado', 'nombres', 'apellidos', 'persona_idno']
    ordering_fields = ['nombre_normalizado', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def get_export_filename(self):
        return "personas_no_esclavizadas_export.csv"

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.action == 'list':
            queryset = queryset.prefetch_related(
                'relaciones', 'p_x_l_pere', 'ocupaciones', 'calidades',
            )
        elif self.action == 'retrieve':
            queryset = queryset.prefetch_related(
                'documentos__archivo',
                'relaciones__personas',
                Prefetch('p_x_l_pere',
                         queryset=PersonaLugarRel.objects.select_related(
                             'lugar', 'situacion_lugar', 'documento'
                         ).order_by('ordinal')),
            )
        
        return queryset

    @action(detail=False, methods=['get'])
    def search(self, request):
        """PostgreSQL full-text and trigram search for non-enslaved persons. Quotes for exact match."""
        raw_query = request.query_params.get('q', '')
        if not raw_query:
            return Response({'error': 'No query provided'}, status=400)

        try:
            query, is_exact = parse_search_query(raw_query)
            search_type = 'phrase' if is_exact else 'plain'
            search_query = SearchQuery(query, config='spanish', search_type=search_type)

            queryset = PersonaNoEsclavizada.objects.annotate(
                search_rank=SearchRank(F('search_vector'), search_query),
                nombre_similarity=TrigramSimilarity('nombre_normalizado', query),
                nombres_similarity=TrigramSimilarity('nombres', query)
            )

            if is_exact:
                queryset = queryset.filter(search_vector=search_query)
            else:
                queryset = queryset.filter(
                    Q(search_vector=search_query) |
                    Q(nombre_similarity__gt=0.3) |
                    Q(nombres_similarity__gt=0.3)
                )

            queryset = queryset.filter(
                is_published=True
            ).order_by(
                '-search_rank',
                '-nombre_similarity',
                '-updated_at'
            ).distinct()
            
            page = self.paginate_queryset(queryset)
            
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error executing search: {str(e)}")
            return Response({'error': 'An error occurred during the search'}, status=500)

    @action(detail=True, methods=['get'])
    def history(self, request, persona_id=None):
        """Get change history for this persona"""
        persona = self.get_object()
        history_records = persona.history.all().order_by('-history_date')
        
        page = self.paginate_queryset(history_records)
        if page is not None:
            serializer = PersonaHistorySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = PersonaHistorySerializer(history_records, many=True)
        return Response(serializer.data)


# Lugar ViewSet
class LugarViewSet(BaseV2ViewSet):
    queryset = Lugar.objects.all()
    serializer_class = LugarListSerializer
    list_serializer_class = LugarListSerializer
    detail_serializer_class = LugarDetailSerializer
    write_serializer_class = LugarWriteSerializer
    lookup_field = 'lugar_id'
    filterset_fields = {
        'tipo': ['exact'],
    }
    search_fields = ['nombre_lugar', 'otros_nombres']
    ordering_fields = ['nombre_lugar', 'tipo', 'created_at', 'updated_at']
    ordering = ['nombre_lugar']

    def get_export_filename(self):
        return "lugares_export.csv"

    @action(detail=False, methods=['get'])
    def search(self, request):
        """PostgreSQL full-text and trigram search for places. Quotes for exact match."""
        raw_query = request.query_params.get('q', '')
        if not raw_query:
            return Response({'error': 'No query provided'}, status=400)

        try:
            query, is_exact = parse_search_query(raw_query)
            search_type = 'phrase' if is_exact else 'plain'
            search_query = SearchQuery(query, config='spanish', search_type=search_type)

            queryset = Lugar.objects.annotate(
                search_rank=SearchRank(F('search_vector'), search_query),
                nombre_similarity=TrigramSimilarity('nombre_lugar', query)
            )

            if is_exact:
                queryset = queryset.filter(search_vector=search_query)
            else:
                queryset = queryset.filter(
                    Q(search_vector=search_query) |
                    Q(nombre_similarity__gt=0.3)
                )

            queryset = queryset.order_by(
                '-search_rank',
                '-nombre_similarity',
                '-updated_at'
            ).distinct()
            
            page = self.paginate_queryset(queryset)
            
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error executing search: {str(e)}")
            return Response({'error': 'An error occurred during the search'}, status=500)

    @action(detail=True, methods=['get'])
    def personas(self, request, lugar_id=None):
        """Get PersonaLugarRel records for this lugar, with nested personas and documento."""
        lugar = self.get_object()
        rels = (
            PersonaLugarRel.objects
            .filter(lugar=lugar)
            .select_related('documento', 'situacion_lugar')
            .prefetch_related('personas')
            .order_by('ordinal', 'fecha_inicial_lugar')
        )
        page = self.paginate_queryset(rels)
        if page is not None:
            serializer = LugarPersonasRelSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = LugarPersonasRelSerializer(rels, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def procedencia(self, request, lugar_id=None):
        """Get PersonaEsclavizada whose procedencia is this lugar."""
        lugar = self.get_object()
        personas = lugar.procedencia_persona_esclavizada.select_related().all()
        page = self.paginate_queryset(personas)
        if page is not None:
            serializer = PersonaListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = PersonaListSerializer(personas, many=True)
        return Response(serializer.data)


# Corporacion ViewSet
class CorporacionViewSet(DocumentoLinkMixin, BaseV2ViewSet):
    queryset = Corporacion.objects.select_related('lugar_corporacion', 'tipo_institucion').prefetch_related('documentos', 'personas_asociadas').all()
    serializer_class = CorporacionListSerializer
    list_serializer_class = CorporacionListSerializer
    detail_serializer_class = CorporacionDetailSerializer
    write_serializer_class = CorporacionWriteSerializer
    lookup_field = 'corporacion_id'
    filterset_fields = {
        'tipo_institucion__tipo': ['exact', 'icontains'],
        'documentos__documento_id': ['exact'],
    }
    search_fields = ['nombre_institucion', 'nombres_alternativos']
    ordering_fields = ['nombre_institucion', 'created_at', 'updated_at']
    ordering = ['nombre_institucion']

    def get_export_filename(self):
        return "corporaciones_export.csv"

    @action(detail=False, methods=['get'])
    def search(self, request):
        """PostgreSQL full-text and trigram search for corporations. Quotes for exact match."""
        raw_query = request.query_params.get('q', '')
        if not raw_query:
            return Response({'error': 'No query provided'}, status=400)

        try:
            query, is_exact = parse_search_query(raw_query)
            search_type = 'phrase' if is_exact else 'plain'
            search_query = SearchQuery(query, config='spanish', search_type=search_type)

            queryset = Corporacion.objects.annotate(
                search_rank=SearchRank(F('search_vector'), search_query),
                nombre_similarity=TrigramSimilarity('nombre_institucion', query)
            )

            if is_exact:
                queryset = queryset.filter(search_vector=search_query)
            else:
                queryset = queryset.filter(
                    Q(search_vector=search_query) |
                    Q(nombre_similarity__gt=0.3)
                )

            queryset = queryset.filter(
                is_published=True
            ).order_by(
                '-search_rank',
                '-nombre_similarity',
                '-updated_at'
            ).distinct()
            
            page = self.paginate_queryset(queryset)
            
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error executing search: {str(e)}")
            return Response({'error': 'An error occurred during the search'}, status=500)

    @action(detail=True, methods=['get'])
    def history(self, request, corporacion_id=None):
        """Get change history for this corporacion"""
        corporacion = self.get_object()
        history_records = corporacion.history.all().order_by('-history_date')
        
        page = self.paginate_queryset(history_records)
        if page is not None:
            serializer = CorporacionHistorySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = CorporacionHistorySerializer(history_records, many=True)
        return Response(serializer.data)


# Relationship ViewSets
class PersonaRelacionesViewSet(viewsets.ModelViewSet):
    """ViewSet for persona relationships"""
    queryset = PersonaRelaciones.objects.select_related('documento').prefetch_related('personas').all()
    serializer_class = PersonaRelacionesDetailSerializer
    write_serializer_class = PersonaRelacionesWriteSerializer
    pagination_class = CustomPagination
    lookup_field = 'persona_relacion_id'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {'documento__documento_id': ['exact']}

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated()]
        return [APIPerm()]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return self.write_serializer_class
        return self.serializer_class


class PersonaLugarRelViewSet(viewsets.ModelViewSet):
    """ViewSet for persona-lugar relationships"""
    queryset = PersonaLugarRel.objects.select_related('documento', 'lugar').prefetch_related('personas').all()
    serializer_class = PersonaLugarRelDetailSerializer
    write_serializer_class = PersonaLugarRelWriteSerializer
    pagination_class = CustomPagination
    lookup_field = 'persona_x_lugares'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {'documento__documento_id': ['exact']}

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy',
                           'bulk_update_ordinal'):
            return [IsAuthenticated()]
        return [APIPerm()]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return self.write_serializer_class
        return self.serializer_class

    @action(detail=False, methods=['patch'], url_path='bulk-ordinal')
    def bulk_update_ordinal(self, request):
        """
        PATCH /api/v2/relaciones-lugares/bulk-ordinal/
        Body: [{"persona_x_lugares": 1, "ordinal": -1}, ...]
        Updates ordinals in bulk for swimlane drag-and-drop.
        """
        items = request.data
        if not isinstance(items, list):
            return Response({'error': 'Expected a list.'}, status=status.HTTP_400_BAD_REQUEST)
        errors = []
        for item in items:
            pk = item.get('persona_x_lugares')
            ordinal = item.get('ordinal')
            if pk is None or ordinal is None:
                errors.append({'item': item, 'error': 'persona_x_lugares and ordinal are required.'})
                continue
            if ordinal == 0:
                errors.append({'item': item, 'error': '0 no es un valor permitido para el ordinal.'})
                continue
            try:
                PersonaLugarRel.objects.filter(persona_x_lugares=pk).update(ordinal=ordinal)
            except Exception as e:
                errors.append({'item': item, 'error': str(e)})
        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status': 'updated'})


# ── Vocabulary ViewSets ───────────────────────────────────────────────────────

class VocabBaseViewSet(viewsets.ModelViewSet):
    """Base for simple vocabulary (lookup table) ViewSets.

    List/retrieve are public; writes require authentication.
    """
    pagination_class = None  # return full list — these are small tables
    filter_backends = [SearchFilter]

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated()]
        return [APIPerm()]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return getattr(self, 'write_serializer_class', self.serializer_class)
        return self.serializer_class


class TipoDocumentalViewSet(VocabBaseViewSet):
    from dbgestor.models import TipoDocumental as _TipoDocumental
    queryset = TipoDocumental.objects.all()
    serializer_class = TipoDocumentalWriteSerializer
    search_fields = ['tipo_documental']
    lookup_field = 'pk'


class CalidadesViewSet(VocabBaseViewSet):
    queryset = Calidades.objects.all()
    serializer_class = CalidadesWriteSerializer
    search_fields = ['calidad']
    lookup_field = 'calidad_id'


class HispanizacionesViewSet(VocabBaseViewSet):
    queryset = Hispanizaciones.objects.all()
    serializer_class = HispanizacionesWriteSerializer
    search_fields = ['hispanizacion']
    lookup_field = 'hispanizacion_id'


class EtnonimosViewSet(VocabBaseViewSet):
    queryset = Etonimos.objects.all()
    serializer_class = EtnonimosWriteSerializer
    search_fields = ['etonimo']
    lookup_field = 'etonimo_id'


class EstadoCivilViewSet(VocabBaseViewSet):
    queryset = EstadoCivil.objects.all()
    serializer_class = EstadoCivilWriteSerializer
    search_fields = ['estado_civil']
    lookup_field = 'estado_civil_id'


class ActividadesViewSet(VocabBaseViewSet):
    queryset = ActividadesModel.objects.all()
    serializer_class = ActividadesWriteSerializer
    search_fields = ['actividad']
    lookup_field = 'actividad_id'


class SituacionLugarViewSet(VocabBaseViewSet):
    queryset = SituacionLugar.objects.all()
    serializer_class = SituacionLugarWriteSerializer
    search_fields = ['situacion']
    lookup_field = 'situacion_id'


class RolEventoViewSet(VocabBaseViewSet):
    queryset = RolEvento.objects.all()
    serializer_class = RolEventoWriteSerializer
    search_fields = ['rol_evento']
    lookup_field = 'pk'


class TiposInstitucionViewSet(VocabBaseViewSet):
    queryset = TiposInstitucion.objects.all()
    serializer_class = TiposInstitucionWriteSerializer
    search_fields = ['tipo']
    lookup_field = 'tipo_id'


# Global Search API
class SearchAPIView(APIView):
    """
    Unified search + browse endpoint.

    When ``q`` is provided, performs PostgreSQL full-text search with relevance
    ranking.  When ``q`` is absent, returns *all* published records (browse mode)
    with server-side ordering, filtering, and pagination.

    Returns:
        {results, count, next, previous, typeCounts, facets}

    Query params:
        q               – search query (optional; omit for browse mode)
        type            – entity type: documento, personaesclavizada, … (default: all)
        page            – page number (default: 1)
        page_size       – results per page (default: 30, max: 300)
        ordering        – field name, prefix with ``-`` for descending
        search          – simple text filter (icontains) for browse mode

    Filter params (comma-separated):
        lugar_id, archivo_id, year, etnonimo, calidad, hispanizacion, ocupacion

    Form-based filter params (DRF-style per-entity fields):
        sexo, honorifico, edad__gte, edad__lte, tipo,
        tipo_documento__tipo_documental__icontains,
        etnonimos__etonimo__icontains, hispanizacion__hispanizacion__icontains,
        fecha_inicial__gte, fecha_inicial__lte, fecha_final__gte, fecha_final__lte,
        tipo_institucion__tipo__icontains
    """
    permission_classes = [APIPerm]
    DEFAULT_PAGE_SIZE = 30
    MAX_PAGE_SIZE = 300

    # Allowed ordering fields per entity type (whitelist)
    ORDERING_FIELDS = {
        'documento': {'titulo', 'fecha_inicial', 'fecha_final', 'created_at', 'updated_at'},
        'personaesclavizada': {'nombre_normalizado', 'edad', 'created_at', 'updated_at', 'fecha_nacimiento', 'earliest_doc_date', 'latest_doc_date'},
        'personanoesclavizada': {'nombre_normalizado', 'created_at', 'updated_at'},
        'lugar': {'nombre_lugar', 'tipo', 'created_at', 'updated_at'},
        'corporacion': {'nombre_institucion', 'created_at', 'updated_at'},
    }

    DEFAULT_ORDERING = {
        'documento': '-created_at',
        'personaesclavizada': '-created_at',
        'personanoesclavizada': '-created_at',
        'lugar': 'nombre_lugar',
        'corporacion': '-created_at',
    }

    TYPE_CONFIGS = {
        'documento': (Documento, 'titulo', DocumentoListSerializer),
        'personaesclavizada': (PersonaEsclavizada, 'nombre_normalizado', PersonaEsclavizadaListSerializer),
        'personanoesclavizada': (PersonaNoEsclavizada, 'nombre_normalizado', PersonaNoEsclavizadaListSerializer),
        'lugar': (Lugar, 'nombre_lugar', LugarListSerializer),
        'corporacion': (Corporacion, 'nombre_institucion', CorporacionListSerializer),
    }

    # DRF-style search fields per entity type (for the `search` param)
    SEARCH_FIELDS = {
        'documento': ['titulo', 'descripcion', 'documento_idno'],
        'personaesclavizada': ['nombre_normalizado', 'nombres', 'apellidos', 'persona_idno'],
        'personanoesclavizada': ['nombre_normalizado', 'nombres', 'apellidos', 'persona_idno'],
        'lugar': ['nombre_lugar', 'otros_nombres'],
        'corporacion': ['nombre_institucion'],
    }

    # ── helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _csv_ints(request, key):
        raw = request.query_params.get(key, '')
        return [int(v) for v in raw.split(',') if v.strip().isdigit()] if raw else []

    @staticmethod
    def _csv_strs(request, key):
        raw = request.query_params.get(key, '')
        return [v.strip() for v in raw.split(',') if v.strip()] if raw else []

    def _text_match(self, model, search_query, similarity_field, query_text, is_exact):
        """Return annotated queryset with text-match filter applied."""
        qs = model.objects.annotate(
            search_rank=SearchRank(F('search_vector'), search_query),
            name_similarity=TrigramSimilarity(similarity_field, query_text),
        )
        if is_exact:
            qs = qs.filter(search_vector=search_query)
        else:
            qs = qs.filter(Q(search_vector=search_query) | Q(name_similarity__gt=0.3))
        return qs

    def _apply_filters(self, qs, type_key, filters):
        """Apply sidebar filters to a queryset (type-aware)."""
        lugar_ids = filters.get('lugar_id', [])
        archivo_ids = filters.get('archivo_id', [])
        years = filters.get('year', [])
        etnonimos = filters.get('etnonimo', [])
        calidades = filters.get('calidad', [])
        hispanizaciones = filters.get('hispanizacion', [])
        ocupaciones = filters.get('ocupacion', [])

        if type_key == 'documento':
            if lugar_ids:
                qs = qs.filter(lugar_de_produccion__lugar_id__in=lugar_ids)
            if archivo_ids:
                qs = qs.filter(archivo__archivo_id__in=archivo_ids)
            if years:
                qs = qs.filter(fecha_inicial__year__in=years)
        elif type_key in ('personaesclavizada', 'personanoesclavizada'):
            if lugar_ids:
                qs = qs.filter(p_x_l_pere__lugar__lugar_id__in=lugar_ids).distinct()
            if archivo_ids:
                qs = qs.filter(documentos__archivo__archivo_id__in=archivo_ids).distinct()
            if years:
                qs = qs.filter(documentos__fecha_inicial__year__in=years).distinct()
            if calidades:
                qs = qs.filter(calidades__calidad__in=calidades).distinct()
            if ocupaciones:
                qs = qs.filter(ocupaciones__actividad__in=ocupaciones).distinct()
            if type_key == 'personaesclavizada':
                if etnonimos:
                    qs = qs.filter(etnonimos__etonimo__in=etnonimos).distinct()
                if hispanizaciones:
                    qs = qs.filter(hispanizacion__hispanizacion__in=hispanizaciones).distinct()
        elif type_key == 'lugar':
            if lugar_ids:
                qs = qs.filter(lugar_id__in=lugar_ids)
        elif type_key == 'corporacion':
            if lugar_ids:
                qs = qs.filter(lugar_corporacion__lugar_id__in=lugar_ids)
            if archivo_ids:
                qs = qs.filter(documentos__archivo__archivo_id__in=archivo_ids).distinct()

        return qs

    def _apply_form_filters(self, qs, type_key, request):
        """Apply DRF-style form-based filter params (from BrowseFilters sidebar)."""
        p = request.query_params

        if type_key in ('personaesclavizada', 'personanoesclavizada'):
            if p.get('sexo'):
                qs = qs.filter(sexo=p['sexo'])
            if type_key == 'personanoesclavizada' and p.get('honorifico'):
                qs = qs.filter(honorifico=p['honorifico'])
            if p.get('calidades__calidad__icontains'):
                qs = qs.filter(calidades__calidad__icontains=p['calidades__calidad__icontains']).distinct()
            if p.get('trayectoria_lugar'):
                lugar_ids = [int(x) for x in p['trayectoria_lugar'].split(',') if x.strip().isdigit()]
                if lugar_ids:
                    for lid in lugar_ids:
                        qs = qs.filter(p_x_l_pere__lugar__lugar_id=lid)
                    qs = qs.distinct()
            if type_key == 'personanoesclavizada':
                if p.get('ocupaciones__actividad__icontains'):
                    qs = qs.filter(ocupaciones__actividad__icontains=p['ocupaciones__actividad__icontains']).distinct()
            if type_key == 'personaesclavizada':
                if p.get('edad__gte'):
                    qs = qs.filter(edad__gte=int(p['edad__gte']))
                if p.get('edad__lte'):
                    qs = qs.filter(edad__lte=int(p['edad__lte']))
                if p.get('etnonimos__etonimo__icontains'):
                    qs = qs.filter(etnonimos__etonimo__icontains=p['etnonimos__etonimo__icontains']).distinct()
                if p.get('hispanizacion__hispanizacion__icontains'):
                    qs = qs.filter(hispanizacion__hispanizacion__icontains=p['hispanizacion__hispanizacion__icontains']).distinct()
                if p.get('procedencia'):
                    qs = qs.filter(procedencia__lugar_id=int(p['procedencia']))
                if p.get('fecha_documento__gte'):
                    val = p['fecha_documento__gte']
                    if len(val) == 4 and val.isdigit():
                        val = f"{val}-01-01"
                    qs = qs.filter(documentos__fecha_inicial__gte=val).distinct()
                if p.get('fecha_documento__lte'):
                    val = p['fecha_documento__lte']
                    if len(val) == 4 and val.isdigit():
                        val = f"{val}-12-31"
                    qs = qs.filter(documentos__fecha_inicial__lte=val).distinct()

        elif type_key == 'documento':
            if p.get('tipo_documento__tipo_documental__icontains'):
                qs = qs.filter(tipo_documento__tipo_documental__icontains=p['tipo_documento__tipo_documental__icontains'])
            if p.get('fecha_inicial__gte'):
                qs = qs.filter(fecha_inicial__gte=p['fecha_inicial__gte'])
            if p.get('fecha_inicial__lte'):
                qs = qs.filter(fecha_inicial__lte=p['fecha_inicial__lte'])
            if p.get('fecha_final__gte'):
                qs = qs.filter(fecha_final__gte=p['fecha_final__gte'])
            if p.get('fecha_final__lte'):
                qs = qs.filter(fecha_final__lte=p['fecha_final__lte'])

        elif type_key == 'lugar':
            if p.get('tipo'):
                qs = qs.filter(tipo=p['tipo'])

        elif type_key == 'corporacion':
            if p.get('tipo_institucion__tipo__icontains'):
                qs = qs.filter(tipo_institucion__tipo__icontains=p['tipo_institucion__tipo__icontains'])
            if p.get('lugar_corporacion__nombre_lugar__icontains'):
                qs = qs.filter(lugar_corporacion__nombre_lugar__icontains=p['lugar_corporacion__nombre_lugar__icontains'])

        return qs

    def _apply_simple_search(self, qs, type_key, text):
        """Apply simple icontains search (browse-mode text filter in sidebar)."""
        fields = self.SEARCH_FIELDS.get(type_key, [])
        if not fields:
            return qs
        q_objects = Q()
        for field in fields:
            q_objects |= Q(**{f'{field}__icontains': text})
        return qs.filter(q_objects).distinct()

    def _validate_ordering(self, ordering_param, type_key):
        """Return validated ordering string or default for the entity type."""
        if not ordering_param:
            return self.DEFAULT_ORDERING.get(type_key, '-created_at')
        field = ordering_param.lstrip('-')
        allowed = self.ORDERING_FIELDS.get(type_key, set())
        if field in allowed:
            return ordering_param
        return self.DEFAULT_ORDERING.get(type_key, '-created_at')

    # ── facets ─────────────────────────────────────────────────────────

    def _collect_facets(self, querysets_by_type):
        """
        Build facet buckets from the *full* (unfiltered-by-sidebar) querysets
        so the user always sees what is available.
        """
        lugar_counts = {}
        archivo_counts = {}
        year_set = set()
        etnonimo_counts = {}
        calidad_counts = {}
        hispanizacion_counts = {}
        ocupacion_counts = {}
        procedencia_counts = {}

        for type_key, qs in querysets_by_type.items():
            # ── Lugares ───
            if type_key == 'documento':
                for row in qs.filter(lugar_de_produccion__isnull=False).values(
                        'lugar_de_produccion__lugar_id', 'lugar_de_produccion__nombre_lugar'
                ).annotate(c=Count('documento_id')):
                    lid = row['lugar_de_produccion__lugar_id']
                    lugar_counts.setdefault(lid, {'id': lid, 'nombre': row['lugar_de_produccion__nombre_lugar'], 'count': 0})
                    lugar_counts[lid]['count'] += row['c']
            elif type_key in ('personaesclavizada', 'personanoesclavizada'):
                for row in qs.filter(p_x_l_pere__lugar__isnull=False).values(
                        'p_x_l_pere__lugar__lugar_id', 'p_x_l_pere__lugar__nombre_lugar'
                ).annotate(c=Count('persona_id', distinct=True)):
                    lid = row['p_x_l_pere__lugar__lugar_id']
                    lugar_counts.setdefault(lid, {'id': lid, 'nombre': row['p_x_l_pere__lugar__nombre_lugar'], 'count': 0})
                    lugar_counts[lid]['count'] += row['c']

            # ── Archivos ──
            if type_key == 'documento':
                for row in qs.values('archivo__archivo_id', 'archivo__nombre').annotate(c=Count('documento_id')):
                    aid = row['archivo__archivo_id']
                    archivo_counts.setdefault(aid, {'id': aid, 'nombre': row['archivo__nombre'], 'count': 0})
                    archivo_counts[aid]['count'] += row['c']
            elif type_key in ('personaesclavizada', 'personanoesclavizada'):
                for row in qs.filter(documentos__isnull=False).values(
                        'documentos__archivo__archivo_id', 'documentos__archivo__nombre'
                ).annotate(c=Count('persona_id', distinct=True)):
                    aid = row['documentos__archivo__archivo_id']
                    if aid:
                        archivo_counts.setdefault(aid, {'id': aid, 'nombre': row['documentos__archivo__nombre'], 'count': 0})
                        archivo_counts[aid]['count'] += row['c']

            # ── Años ──
            if type_key == 'documento':
                for row in qs.filter(fecha_inicial__isnull=False).annotate(
                        y=ExtractYear('fecha_inicial')).values('y').annotate(c=Count('documento_id')):
                    year_set.add(row['y'])
            elif type_key in ('personaesclavizada', 'personanoesclavizada'):
                for row in qs.filter(documentos__fecha_inicial__isnull=False).annotate(
                        y=ExtractYear('documentos__fecha_inicial')).values('y').annotate(
                        c=Count('persona_id', distinct=True)):
                    year_set.add(row['y'])

            # ── Persona-specific facets ──
            if type_key in ('personaesclavizada', 'personanoesclavizada'):
                for row in qs.filter(calidades__isnull=False).values(
                        'calidades__calidad').annotate(c=Count('persona_id', distinct=True)):
                    label = row['calidades__calidad']
                    calidad_counts[label] = calidad_counts.get(label, 0) + row['c']

                for row in qs.filter(ocupaciones__isnull=False).values(
                        'ocupaciones__actividad').annotate(c=Count('persona_id', distinct=True)):
                    label = row['ocupaciones__actividad']
                    ocupacion_counts[label] = ocupacion_counts.get(label, 0) + row['c']

            if type_key == 'personaesclavizada':
                for row in qs.filter(etnonimos__isnull=False).values(
                        'etnonimos__etonimo').annotate(c=Count('persona_id', distinct=True)):
                    label = row['etnonimos__etonimo']
                    etnonimo_counts[label] = etnonimo_counts.get(label, 0) + row['c']

                for row in qs.filter(hispanizacion__isnull=False).values(
                        'hispanizacion__hispanizacion').annotate(c=Count('persona_id', distinct=True)):
                    label = row['hispanizacion__hispanizacion']
                    hispanizacion_counts[label] = hispanizacion_counts.get(label, 0) + row['c']

                for row in qs.filter(procedencia__isnull=False).values(
                        'procedencia__lugar_id', 'procedencia__nombre_lugar'
                ).annotate(c=Count('persona_id', distinct=True)):
                    lid = row['procedencia__lugar_id']
                    procedencia_counts.setdefault(lid, {'id': lid, 'label': row['procedencia__nombre_lugar'], 'count': 0})
                    procedencia_counts[lid]['count'] += row['c']

        # ── Build hierarchical year tree (century → decade → year) ────
        century_labels = {16: 'XVI', 17: 'XVII', 18: 'XVIII', 19: 'XIX', 20: 'XX'}
        years_tree = {}
        for y in sorted(year_set):
            c = y // 100 + 1
            century = f"Siglo {century_labels.get(c, str(c))}"
            decade = (y // 10) * 10
            years_tree.setdefault(century, {})
            years_tree[century].setdefault(decade, [])
            years_tree[century][decade].append(y)

        return {
            'lugares': sorted(lugar_counts.values(), key=lambda x: -x['count']),
            'archivos': sorted(archivo_counts.values(), key=lambda x: -x['count']),
            'fechas': years_tree,
            'year_range': {'min': min(year_set), 'max': max(year_set)} if year_set else None,
            'etnonimos': sorted(
                [{'label': k, 'count': v} for k, v in etnonimo_counts.items()],
                key=lambda x: -x['count']),
            'calidades': sorted(
                [{'label': k, 'count': v} for k, v in calidad_counts.items()],
                key=lambda x: -x['count']),
            'hispanizaciones': sorted(
                [{'label': k, 'count': v} for k, v in hispanizacion_counts.items()],
                key=lambda x: -x['count']),
            'ocupaciones': sorted(
                [{'label': k, 'count': v} for k, v in ocupacion_counts.items()],
                key=lambda x: -x['count']),
            'procedencias': sorted(procedencia_counts.values(), key=lambda x: -x['count']),
        }

    # ── main handler ──────────────────────────────────────────────────

    def get(self, request):
        query_text = request.query_params.get('q', '').strip()
        entity_type = request.query_params.get('type', 'all')
        page_number = max(int(request.query_params.get('page', 1)), 1)
        page_size = min(
            max(int(request.query_params.get('page_size', self.DEFAULT_PAGE_SIZE)), 1),
            self.MAX_PAGE_SIZE,
        )
        ordering_param = request.query_params.get('ordering', '')
        search_text = request.query_params.get('search', '').strip()

        is_search = bool(query_text)

        try:
            # ── Determine which entity types to query ──────────────
            requested_types = (
                [t.strip() for t in entity_type.split(',') if t.strip()]
                if entity_type != 'all' else []
            )
            active_types = (
                [t for t in requested_types if t in self.TYPE_CONFIGS]
                if requested_types
                else list(self.TYPE_CONFIGS.keys())
            )

            # Parse sidebar filter params
            filters = {
                'lugar_id': self._csv_ints(request, 'lugar_id'),
                'archivo_id': self._csv_ints(request, 'archivo_id'),
                'year': self._csv_ints(request, 'year'),
                'etnonimo': self._csv_strs(request, 'etnonimo'),
                'calidad': self._csv_strs(request, 'calidad'),
                'hispanizacion': self._csv_strs(request, 'hispanizacion'),
                'ocupacion': self._csv_strs(request, 'ocupacion'),
            }
            has_filters = any(v for v in filters.values())

            if is_search:
                # ── FTS mode: annotate + rank ──────────────────────
                clean_query, is_exact = parse_search_query(query_text)
                search_type = 'phrase' if is_exact else 'plain'
                search_query = SearchQuery(clean_query, config='spanish', search_type=search_type)

                base_querysets = {}
                for tk, (model, sim_field, _) in self.TYPE_CONFIGS.items():
                    base_querysets[tk] = self._text_match(
                        model, search_query, sim_field, clean_query, is_exact)
            else:
                # ── Browse mode: all records ───────────────────────
                base_querysets = {}
                for tk, (model, _, _) in self.TYPE_CONFIGS.items():
                    base_querysets[tk] = model.objects.all()

            # ── Prefetch for list serializer fields ──────────────
            if 'personaesclavizada' in base_querysets:
                base_querysets['personaesclavizada'] = base_querysets['personaesclavizada'].prefetch_related(
                    'documentos', 'etnonimos', 'hispanizacion', 'calidades', 'relaciones', 'p_x_l_pere',
                ).annotate(
                    earliest_doc_date=Min('documentos__fecha_inicial'),
                    latest_doc_date=Max('documentos__fecha_inicial'),
                )
            if 'personanoesclavizada' in base_querysets:
                base_querysets['personanoesclavizada'] = base_querysets['personanoesclavizada'].prefetch_related(
                    'documentos', 'relaciones', 'p_x_l_pere', 'ocupaciones', 'calidades',
                )

            # ── Facets (from unfiltered base querysets) ────────────
            facets = self._collect_facets(
                {tk: qs for tk, qs in base_querysets.items() if tk in active_types})

            # ── Type counts (unfiltered) ──────────────────────────
            # In search mode, return counts for ALL entity types so the
            # frontend can show badges like enslaved.org does.
            count_types = list(self.TYPE_CONFIGS.keys()) if is_search else active_types
            type_counts = {tk: base_querysets[tk].count() for tk in count_types}

            # ── Apply all filters per entity type + paginate ──────
            # In unified mode we query one entity type at a time (the
            # active tab) so we can do proper DB-level pagination.
            # When multiple types are active, we merge across types.
            results_data = []
            total_count = 0

            if len(active_types) == 1:
                # ── Single entity type → efficient DB pagination ───
                tk = active_types[0]
                _, _, serializer_cls = self.TYPE_CONFIGS[tk]
                qs = base_querysets[tk]

                # Sidebar facet filters
                if has_filters:
                    qs = self._apply_filters(qs, tk, filters)

                # Form-based filters
                qs = self._apply_form_filters(qs, tk, request)

                # Simple text search (browse mode sidebar)
                if search_text:
                    qs = self._apply_simple_search(qs, tk, search_text)

                # Ordering
                if is_search:
                    if ordering_param:
                        validated = self._validate_ordering(ordering_param, tk)
                        qs = qs.order_by(validated)
                    else:
                        qs = qs.order_by('-search_rank', '-name_similarity')
                else:
                    validated = self._validate_ordering(ordering_param, tk)
                    qs = qs.order_by(validated)

                total_count = qs.count()
                start = (page_number - 1) * page_size
                end = start + page_size
                page_qs = qs[start:end]

                results_data = [
                    {'type': tk, 'source': serializer_cls(obj).data}
                    for obj in page_qs
                ]
            else:
                # ── Multiple entity types → in-memory merge ────────
                all_items = []
                for tk in active_types:
                    _, _, serializer_cls = self.TYPE_CONFIGS[tk]
                    qs = base_querysets[tk]

                    if has_filters:
                        qs = self._apply_filters(qs, tk, filters)
                    qs = self._apply_form_filters(qs, tk, request)
                    if search_text:
                        qs = self._apply_simple_search(qs, tk, search_text)

                    if is_search:
                        qs = qs.order_by('-search_rank', '-name_similarity')
                    else:
                        validated = self._validate_ordering(ordering_param, tk)
                        qs = qs.order_by(validated)

                    for obj in qs[:500]:  # cap per type to prevent memory issues
                        score = 0
                        if is_search:
                            score = (getattr(obj, 'search_rank', 0) or 0) + (getattr(obj, 'name_similarity', 0) or 0)
                        all_items.append({
                            'type': tk,
                            'score': score,
                            'source': serializer_cls(obj).data,
                        })

                if is_search:
                    all_items.sort(key=lambda x: x['score'], reverse=True)

                total_count = len(all_items)
                start = (page_number - 1) * page_size
                end = start + page_size
                page_items = all_items[start:end]

                results_data = [
                    {'type': item['type'], 'source': item['source']}
                    for item in page_items
                ]

            # ── Build pagination URLs ─────────────────────────────
            total_pages = max((total_count + page_size - 1) // page_size, 1)
            base_url = request.build_absolute_uri().split('?')[0]
            params = request.query_params.copy()

            def build_page_url(p):
                params['page'] = p
                return f"{base_url}?{urlencode(params)}"

            return Response({
                'count': total_count,
                'page_size': page_size,
                'total_pages': total_pages,
                'next': build_page_url(page_number + 1) if page_number < total_pages else None,
                'previous': build_page_url(page_number - 1) if page_number > 1 else None,
                'typeCounts': type_counts,
                'facets': facets,
                'results': results_data,
            })

        except Exception as e:
            logger.error(f"Error in search/browse: {str(e)}")
            return Response({'error': 'An error occurred during the search'}, status=500)


# Travel Trajectory ViewSet
class PersonaTravelTrajectoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for person travel trajectories - optimized for map visualizations
    """
    permission_classes = [APIPerm]
    serializer_class = PersonaTravelTrajectorySerializer
    pagination_class = CustomPagination
    lookup_field = 'persona_id'

    def get_queryset(self):
        # Return personas that have any place association:
        # persona_x_lugares, procedencia, lugar_nacimiento, or lugar_defuncion
        return Persona.objects.filter(
            Q(p_x_l_pere__isnull=False) |
            Q(lugar_nacimiento__isnull=False) |
            Q(lugar_defuncion__isnull=False) |
            Q(personaesclavizada__procedencia__isnull=False)
        ).distinct()

    @action(detail=True, methods=['get'])
    def trajectory_details(self, request, persona_id=None):
        """Get detailed trajectory points for a specific person"""
        persona = self.get_object()
        trajectories = persona.p_x_l_pere.select_related('lugar', 'documento', 'situacion_lugar').all().order_by('ordinal')
        
        serializer = TravelTrajectorySerializer(trajectories, many=True)
        return Response({
            'persona_id': persona.persona_id,
            'persona_idno': persona.persona_idno,
            'nombre_normalizado': persona.nombre_normalizado,
            'trajectory_count': trajectories.count(),
            'trajectories': serializer.data
        })

    @action(detail=False, methods=['get'])
    def all_trajectories_summary(self, request):
        """Get summary of all trajectories for map overview, including FK places."""
        # Build a dict of lugar_id → aggregated counts
        place_map = {}

        def _add_place(lugar_id, nombre, tipo, lat, lon, traj_count, pers_count):
            if lat is None or lon is None:
                return
            if lugar_id in place_map:
                place_map[lugar_id]['trajectory_count'] += traj_count
                place_map[lugar_id]['persona_count'] += pers_count
            else:
                place_map[lugar_id] = {
                    'lugar__lugar_id': lugar_id,
                    'lugar__nombre_lugar': nombre,
                    'lugar__tipo': tipo,
                    'lugar__lat': lat,
                    'lugar__lon': lon,
                    'trajectory_count': traj_count,
                    'persona_count': pers_count,
                }

        # 1) PersonaLugarRel places (existing)
        pxl_places = PersonaLugarRel.objects.select_related('lugar').values(
            'lugar__lugar_id', 'lugar__nombre_lugar', 'lugar__tipo', 'lugar__lat', 'lugar__lon'
        ).annotate(
            trajectory_count=Count('persona_x_lugares'),
            persona_count=Count('personas', distinct=True)
        ).filter(lugar__lat__isnull=False, lugar__lon__isnull=False)

        for row in pxl_places:
            _add_place(row['lugar__lugar_id'], row['lugar__nombre_lugar'], row['lugar__tipo'],
                       row['lugar__lat'], row['lugar__lon'], row['trajectory_count'], row['persona_count'])

        # 2) Procedencia places (PersonaEsclavizada only)
        proc_places = (PersonaEsclavizada.objects
                       .filter(procedencia__isnull=False, procedencia__lat__isnull=False, procedencia__lon__isnull=False)
                       .values('procedencia__lugar_id', 'procedencia__nombre_lugar', 'procedencia__tipo',
                               'procedencia__lat', 'procedencia__lon')
                       .annotate(persona_count=Count('persona_id', distinct=True)))
        for row in proc_places:
            _add_place(row['procedencia__lugar_id'], row['procedencia__nombre_lugar'], row['procedencia__tipo'],
                       row['procedencia__lat'], row['procedencia__lon'], 0, row['persona_count'])

        # 3) lugar_nacimiento places
        nac_places = (Persona.objects
                      .filter(lugar_nacimiento__isnull=False, lugar_nacimiento__lat__isnull=False, lugar_nacimiento__lon__isnull=False)
                      .values('lugar_nacimiento__lugar_id', 'lugar_nacimiento__nombre_lugar', 'lugar_nacimiento__tipo',
                              'lugar_nacimiento__lat', 'lugar_nacimiento__lon')
                      .annotate(persona_count=Count('persona_id', distinct=True)))
        for row in nac_places:
            _add_place(row['lugar_nacimiento__lugar_id'], row['lugar_nacimiento__nombre_lugar'], row['lugar_nacimiento__tipo'],
                       row['lugar_nacimiento__lat'], row['lugar_nacimiento__lon'], 0, row['persona_count'])

        # 4) lugar_defuncion places
        def_places = (Persona.objects
                      .filter(lugar_defuncion__isnull=False, lugar_defuncion__lat__isnull=False, lugar_defuncion__lon__isnull=False)
                      .values('lugar_defuncion__lugar_id', 'lugar_defuncion__nombre_lugar', 'lugar_defuncion__tipo',
                              'lugar_defuncion__lat', 'lugar_defuncion__lon')
                      .annotate(persona_count=Count('persona_id', distinct=True)))
        for row in def_places:
            _add_place(row['lugar_defuncion__lugar_id'], row['lugar_defuncion__nombre_lugar'], row['lugar_defuncion__tipo'],
                       row['lugar_defuncion__lat'], row['lugar_defuncion__lon'], 0, row['persona_count'])

        return Response({
            'total_places': len(place_map),
            'places': list(place_map.values())
        })

    # ------------------------------------------------------------------
    # Helpers for aggregated / route_detail
    # ------------------------------------------------------------------

    def _apply_persona_filters(self, qs, params):
        """Apply search filters to a PersonaEsclavizada queryset."""
        sexo = params.get('sexo')
        if sexo:
            qs = qs.filter(sexo=sexo)
        etnonimo = params.get('etnonimo')
        if etnonimo:
            qs = qs.filter(etnonimos__etonimo__icontains=etnonimo)
        calidad = params.get('calidad')
        if calidad:
            qs = qs.filter(calidades__calidad__icontains=calidad)
        hispanizacion = params.get('hispanizacion')
        if hispanizacion:
            qs = qs.filter(hispanizacion__hispanizacion__icontains=hispanizacion)
        edad_gte = params.get('edad__gte')
        if edad_gte and edad_gte.isdigit():
            qs = qs.filter(edad__gte=int(edad_gte))
        edad_lte = params.get('edad__lte')
        if edad_lte and edad_lte.isdigit():
            qs = qs.filter(edad__lte=int(edad_lte))
        fecha_ini = params.get('fecha_inicial__gte')
        if fecha_ini:
            qs = qs.filter(documentos__fecha_inicial__gte=fecha_ini)
        fecha_fin = params.get('fecha_inicial__lte')
        if fecha_fin:
            qs = qs.filter(documentos__fecha_inicial__lte=fecha_fin)
        return qs.distinct()

    def _build_persona_points(self, persona):
        """Return sorted list of trajectory dicts for one persona."""
        rels = (persona.p_x_l_pere
                .select_related('lugar', 'documento')
                .order_by('ordinal'))
        rel_points = []
        for rel in rels:
            lug = rel.lugar
            if lug and lug.lat and lug.lon:
                rel_points.append({
                    'lugar_id': lug.lugar_id,
                    'nombre': lug.nombre_lugar,
                    'lat': float(lug.lat),
                    'lon': float(lug.lon),
                    'ordinal': rel.ordinal,
                })

        min_ord = min((p['ordinal'] for p in rel_points), default=1)
        max_ord = max((p['ordinal'] for p in rel_points), default=0)

        fk_points = []
        seen = set()
        nac = getattr(persona, 'lugar_nacimiento', None)
        if nac and nac.lat and nac.lon:
            fk_points.append({'lugar_id': nac.lugar_id, 'nombre': nac.nombre_lugar,
                              'lat': float(nac.lat), 'lon': float(nac.lon), 'ordinal': min_ord - 2})
            seen.add(nac.lugar_id)
        proc = getattr(persona, 'procedencia', None) if hasattr(persona, 'procedencia') else None
        if proc and proc.lat and proc.lon and proc.lugar_id not in seen:
            fk_points.append({'lugar_id': proc.lugar_id, 'nombre': proc.nombre_lugar,
                              'lat': float(proc.lat), 'lon': float(proc.lon), 'ordinal': min_ord - 1})
        defn = getattr(persona, 'lugar_defuncion', None)
        if defn and defn.lat and defn.lon:
            fk_points.append({'lugar_id': defn.lugar_id, 'nombre': defn.nombre_lugar,
                              'lat': float(defn.lat), 'lon': float(defn.lon), 'ordinal': max_ord + 1})

        return sorted(fk_points + rel_points, key=lambda p: p['ordinal'])

    # ------------------------------------------------------------------
    # Aggregated trajectories
    # ------------------------------------------------------------------

    @action(detail=False, methods=['get'])
    def aggregated(self, request):
        """
        Aggregate all individual trajectories into route flows.
        Returns {routes, places} for Sankey-style map visualization.
        Supports filters: sexo, etnonimo, calidad, hispanizacion,
        edad__gte, edad__lte, fecha_inicial__gte, fecha_inicial__lte.
        """
        qs = PersonaEsclavizada.objects.select_related(
            'procedencia', 'lugar_nacimiento', 'lugar_defuncion'
        ).prefetch_related('p_x_l_pere__lugar', 'p_x_l_pere__documento')
        qs = self._apply_persona_filters(qs, request.query_params)

        # Only personas with at least some place data
        qs = qs.filter(
            Q(p_x_l_pere__isnull=False) |
            Q(lugar_nacimiento__isnull=False) |
            Q(lugar_defuncion__isnull=False) |
            Q(procedencia__isnull=False)
        ).distinct()

        route_map = defaultdict(lambda: {'persona_ids': set()})
        place_map = {}

        def _touch_place(pt):
            pid = pt['lugar_id']
            if pid not in place_map:
                place_map[pid] = {
                    'lugar_id': pid,
                    'nombre': pt['nombre'],
                    'lat': pt['lat'],
                    'lon': pt['lon'],
                    'incoming': 0,
                    'outgoing': 0,
                    'persona_ids': set(),
                }
            return pid

        for persona in qs.iterator(chunk_size=200):
            points = self._build_persona_points(persona)
            if len(points) < 2:
                # Still register single-point personas
                if len(points) == 1:
                    _touch_place(points[0])
                    place_map[points[0]['lugar_id']]['persona_ids'].add(persona.persona_id)
                continue

            for i in range(len(points) - 1):
                fr, to = points[i], points[i + 1]
                if fr['lugar_id'] == to['lugar_id']:
                    continue  # skip self-loops
                fid = _touch_place(fr)
                tid = _touch_place(to)
                place_map[fid]['outgoing'] += 1
                place_map[fid]['persona_ids'].add(persona.persona_id)
                place_map[tid]['incoming'] += 1
                place_map[tid]['persona_ids'].add(persona.persona_id)
                key = (fid, tid)
                route_map[key]['persona_ids'].add(persona.persona_id)

        routes = []
        for (fid, tid), info in route_map.items():
            fp = place_map[fid]
            tp = place_map[tid]
            routes.append({
                'from_lugar_id': fid,
                'from_nombre': fp['nombre'],
                'from_lat': fp['lat'],
                'from_lon': fp['lon'],
                'to_lugar_id': tid,
                'to_nombre': tp['nombre'],
                'to_lat': tp['lat'],
                'to_lon': tp['lon'],
                'count': len(info['persona_ids']),
            })

        places = []
        for pid, info in place_map.items():
            places.append({
                'lugar_id': info['lugar_id'],
                'nombre': info['nombre'],
                'lat': info['lat'],
                'lon': info['lon'],
                'incoming': info['incoming'],
                'outgoing': info['outgoing'],
                'persona_count': len(info['persona_ids']),
            })

        return Response({
            'total_routes': len(routes),
            'total_places': len(places),
            'routes': sorted(routes, key=lambda r: r['count'], reverse=True),
            'places': sorted(places, key=lambda p: p['persona_count'], reverse=True),
        })

    # ------------------------------------------------------------------
    # Route detail
    # ------------------------------------------------------------------

    @action(detail=False, methods=['get'], url_path='route_detail')
    def route_detail(self, request):
        """
        Return paginated persona list for a specific from→to route.
        Query params: from_lugar_id, to_lugar_id (required).
        Same filters as /aggregated/.
        """
        from_id = request.query_params.get('from_lugar_id')
        to_id = request.query_params.get('to_lugar_id')
        if not from_id or not to_id:
            return Response({'detail': 'from_lugar_id and to_lugar_id are required.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            from_id = int(from_id)
            to_id = int(to_id)
        except (ValueError, TypeError):
            return Response({'detail': 'Invalid lugar IDs.'}, status=status.HTTP_400_BAD_REQUEST)

        qs = PersonaEsclavizada.objects.select_related(
            'procedencia', 'lugar_nacimiento', 'lugar_defuncion'
        ).prefetch_related(
            'p_x_l_pere__lugar', 'p_x_l_pere__documento',
            'etnonimos', 'calidades', 'hispanizacion'
        )
        qs = self._apply_persona_filters(qs, request.query_params)
        qs = qs.filter(
            Q(p_x_l_pere__isnull=False) |
            Q(lugar_nacimiento__isnull=False) |
            Q(lugar_defuncion__isnull=False) |
            Q(procedencia__isnull=False)
        ).distinct()

        matching_ids = []
        for persona in qs.iterator(chunk_size=200):
            points = self._build_persona_points(persona)
            for i in range(len(points) - 1):
                if points[i]['lugar_id'] == from_id and points[i + 1]['lugar_id'] == to_id:
                    matching_ids.append(persona.persona_id)
                    break

        # Re-query matched personas with pagination
        result_qs = PersonaEsclavizada.objects.filter(
            persona_id__in=matching_ids
        ).prefetch_related('etnonimos', 'calidades', 'hispanizacion').order_by('nombre_normalizado')

        page = self.paginate_queryset(result_qs)
        data = []
        for p in (page if page is not None else result_qs):
            data.append({
                'persona_id': p.persona_id,
                'nombre_normalizado': p.nombre_normalizado,
                'sexo': p.get_sexo_display() if p.sexo else None,
                'edad': p.edad,
                'etnonimos': [str(e) for e in p.etnonimos.all()],
                'calidades': [str(c) for c in p.calidades.all()],
                'hispanizacion': [str(h) for h in p.hispanizacion.all()],
            })

        if page is not None:
            return self.get_paginated_response(data)
        return Response({'count': len(data), 'results': data})


# Utility Views

class EntityCountsView(APIView):
    """Lightweight endpoint returning record counts for all entity types."""
    permission_classes = [APIPerm]

    def get(self, request):
        return Response({
            'personaesclavizada': PersonaEsclavizada.objects.count(),
            'personanoesclavizada': PersonaNoEsclavizada.objects.count(),
            'documento': Documento.objects.count(),
            'lugar': Lugar.objects.count(),
            'corporacion': Corporacion.objects.count(),
        })


@ensure_csrf_cookie
def get_csrf_token(request):
    """Get CSRF token for the current session."""
    token = get_token(request)
    return JsonResponse({
        'csrfToken': token,
        'detail': 'CSRF cookie set'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def whoami(request):
    user = request.user
    return Response({
        'username': user.username,
        'email': user.email,
        'is_staff': user.is_staff,
        'groups': [g.name for g in user.groups.all()],
        'permissions': list(user.get_all_permissions()),
    })


def api_login(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    data = json.loads(request.body)
    user = authenticate(request, username=data.get('username'), password=data.get('password'))
    if user is not None:
        login(request, user)
        return JsonResponse({
            'username': user.username,
            'email': user.email,
            'is_staff': user.is_staff
        })
    return JsonResponse({'error': 'Invalid credentials'}, status=401)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    logout(request)
    return Response({'success': 'Logged out successfully'})


@api_view(['POST'])
def log_message(request):
    try:
        serializer = LogMessageSerializer(data=request.data)
        if serializer.is_valid():
            level = serializer.validated_data['level'].upper()
            message = serializer.validated_data['message']
            log_method = getattr(logger, level.lower(), logger.info)
            log_method(f'Client log: {message}')
            return Response({'status': 'success'})
        return Response({'status': 'error', 'errors': serializer.errors}, status=400)
    except Exception as e:
        logger.exception(f'Error processing log message: {e}')
        return Response({'status': 'error', 'message': str(e)}, status=500)


# ── Data Visualization endpoints ──────────────────────────────────────

@api_view(['GET'])
def gender_status_distribution(request):
    data = (
        PersonaEsclavizada.objects
        .values('sexo', 'hispanizacion__hispanizacion')
        .annotate(count=Count('persona_idno'))
        .order_by('-count')
    )
    return Response(data)


class PlacesPeopleDistribution(APIView):
    def get(self, request):
        data = (
            PersonaEsclavizada.objects
            .annotate(
                year=ExtractYear('p_x_l_pere__documento__fecha_inicial'),
                lugar=F('p_x_l_pere__lugar__nombre_lugar'),
                tipo=F('p_x_l_pere__lugar__tipo'),
            )
            .values('lugar', 'tipo', 'year')
            .annotate(count=Count('persona_id', distinct=True))
            .filter(lugar__isnull=False, year__isnull=False)
            .order_by('year', 'lugar')
        )
        return Response([
            {"lugar": item['lugar'], "tipo": item['tipo'],
             "year": item['year'], "count": item['count']}
            for item in data
        ])