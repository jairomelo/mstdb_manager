import json
import logging
import re

from django.db.models import Count, F, Q
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
from urllib.parse import urlencode
from rest_framework.pagination import PageNumberPagination
import csv

from dbgestor.models import (Archivo, Documento, PersonaEsclavizada, PersonaNoEsclavizada, Corporacion,
                             PersonaLugarRel, Lugar, PersonaRelaciones, Persona)

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
    
    # Relationship serializers
    PersonaRelacionesDetailSerializer, PersonaLugarRelDetailSerializer,
    PersonaRolEventoDetailSerializer, ActividadesSerializer, LogMessageSerializer,
    
    # Travel trajectory serializers
    TravelTrajectorySerializer, PersonaTravelTrajectorySerializer,
    
    # History serializers
    DocumentoHistorySerializer, PersonaHistorySerializer, CorporacionHistorySerializer
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


# Base ViewSet with common functionality
class BaseV2ViewSet(viewsets.ModelViewSet):
    permission_classes = [APIPerm]
    pagination_class = CustomPagination

    def get_serializer_class(self):
        """
        Return different serializers for list vs detail actions
        """
        if self.action == 'list':
            return getattr(self, 'list_serializer_class', self.serializer_class)
        elif self.action == 'retrieve':
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
    lookup_field = 'documento_id'

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
        personas = documento.personas.all()
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
class PersonaEsclavizadaViewSet(BaseV2ViewSet):
    queryset = PersonaEsclavizada.objects.prefetch_related('documentos', 'ocupaciones').all()
    serializer_class = PersonaEsclavizadaListSerializer
    list_serializer_class = PersonaEsclavizadaListSerializer
    detail_serializer_class = PersonaEsclavizadaDetailSerializer
    lookup_field = 'persona_id'

    def get_export_filename(self):
        return "personas_esclavizadas_export.csv"

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtering
        sexo = self.request.query_params.get('sexo', None)
        if sexo:
            queryset = queryset.filter(sexo=sexo)
        
        edad_min = self.request.query_params.get('edad_min', None)
        if edad_min:
            queryset = queryset.filter(edad__gte=edad_min)
        
        edad_max = self.request.query_params.get('edad_max', None)
        if edad_max:
            queryset = queryset.filter(edad__lte=edad_max)
        
        # Sorting
        sort_by = self.request.query_params.get('sort_by', None)
        if sort_by:
            if sort_by.startswith('-'):
                queryset = queryset.order_by(sort_by)
            else:
                queryset = queryset.order_by(sort_by)
        
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


class PersonaNoEsclavizadaViewSet(BaseV2ViewSet):
    queryset = PersonaNoEsclavizada.objects.prefetch_related('documentos').all()
    serializer_class = PersonaNoEsclavizadaListSerializer
    list_serializer_class = PersonaNoEsclavizadaListSerializer
    detail_serializer_class = PersonaNoEsclavizadaDetailSerializer
    lookup_field = 'persona_id'

    def get_export_filename(self):
        return "personas_no_esclavizadas_export.csv"

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtering
        sexo = self.request.query_params.get('sexo', None)
        if sexo:
            queryset = queryset.filter(sexo=sexo)
        
        # Sorting
        sort_by = self.request.query_params.get('sort_by', None)
        if sort_by:
            queryset = queryset.order_by(sort_by)
        
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
    lookup_field = 'lugar_id'

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
        """Get all personas associated with this lugar"""
        lugar = self.get_object()
        # Get personas through PersonaLugarRel relationship
        personas = Persona.objects.filter(p_x_l_pere__lugar=lugar).distinct()
        page = self.paginate_queryset(personas)
        
        if page is not None:
            serializer = PersonaListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = PersonaListSerializer(personas, many=True)
        return Response(serializer.data)


# Corporacion ViewSet
class CorporacionViewSet(BaseV2ViewSet):
    queryset = Corporacion.objects.select_related('lugar_corporacion', 'tipo_institucion').prefetch_related('documentos', 'personas_asociadas').all()
    serializer_class = CorporacionListSerializer
    list_serializer_class = CorporacionListSerializer
    detail_serializer_class = CorporacionDetailSerializer
    lookup_field = 'corporacion_id'

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
class PersonaRelacionesViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for persona relationships"""
    permission_classes = [APIPerm]
    queryset = PersonaRelaciones.objects.select_related('documento').prefetch_related('personas').all()
    serializer_class = PersonaRelacionesDetailSerializer
    pagination_class = CustomPagination
    lookup_field = 'persona_relacion_id'


class PersonaLugarRelViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for persona-lugar relationships"""
    permission_classes = [APIPerm]
    queryset = PersonaLugarRel.objects.select_related('documento', 'lugar').prefetch_related('personas').all()
    serializer_class = PersonaLugarRelDetailSerializer
    pagination_class = CustomPagination
    lookup_field = 'persona_x_lugares'


# Global Search API
class SearchAPIView(APIView):
    """
    Global search across all entity types using PostgreSQL full-text search.
    Returns a flat, paginated result list compatible with the frontend store:
    {results: [{type, source}], count, next, previous, typeCounts}
    """
    permission_classes = [APIPerm]
    PAGE_SIZE = 20

    def _build_queryset(self, model, search_query, similarity_field, query_text, is_exact):
        """Build an annotated & filtered queryset for a given model."""
        qs = model.objects.annotate(
            search_rank=SearchRank(F('search_vector'), search_query),
            name_similarity=TrigramSimilarity(similarity_field, query_text),
        )
        if is_exact:
            qs = qs.filter(search_vector=search_query)
        else:
            qs = qs.filter(
                Q(search_vector=search_query) | Q(name_similarity__gt=0.3)
            )
        return qs.order_by('-search_rank', '-name_similarity')

    def get(self, request):
        query_text = request.query_params.get('q', '')
        entity_type = request.query_params.get('type', 'all')
        page_number = int(request.query_params.get('page', 1))

        if not query_text:
            return Response({'error': 'No query provided'}, status=400)

        try:
            clean_query, is_exact = parse_search_query(query_text)
            search_type = 'phrase' if is_exact else 'plain'
            search_query = SearchQuery(clean_query, config='spanish', search_type=search_type)

            # ── Collect querysets per type ──────────────────────────
            type_configs = {
                'documento': (Documento, 'titulo', DocumentoListSerializer),
                'personaesclavizada': (PersonaEsclavizada, 'nombre_normalizado', PersonaEsclavizadaListSerializer),
                'personanoesclavizada': (PersonaNoEsclavizada, 'nombre_normalizado', PersonaNoEsclavizadaListSerializer),
                'lugar': (Lugar, 'nombre_lugar', LugarListSerializer),
                'corporacion': (Corporacion, 'nombre_institucion', CorporacionListSerializer),
            }

            # Always compute counts for ALL types (used by filter chips)
            type_counts = {}
            for type_key, (model, sim_field, _) in type_configs.items():
                qs = self._build_queryset(model, search_query, sim_field, clean_query, is_exact)
                type_counts[type_key] = qs.count()

            # ── Build flat result list for requested type(s) ───────
            all_items = []
            active_types = (
                [entity_type] if entity_type != 'all' and entity_type in type_configs
                else type_configs.keys()
            )
            for type_key in active_types:
                model, sim_field, serializer_cls = type_configs[type_key]
                qs = self._build_queryset(model, search_query, sim_field, clean_query, is_exact)
                for obj in qs:
                    all_items.append({
                        'type': type_key,
                        'score': (obj.search_rank or 0) + (obj.name_similarity or 0),
                        'source': serializer_cls(obj).data,
                    })

            # Sort merged list by combined relevance score
            all_items.sort(key=lambda x: x['score'], reverse=True)

            # ── Paginate ───────────────────────────────────────────
            total = len(all_items)
            start = (page_number - 1) * self.PAGE_SIZE
            end = start + self.PAGE_SIZE
            page_items = all_items[start:end]

            # Strip internal score before responding
            for item in page_items:
                item.pop('score', None)

            base_url = request.build_absolute_uri().split('?')[0]
            params = request.query_params.copy()

            def build_page_url(p):
                params['page'] = p
                return f"{base_url}?{urlencode(params)}"

            return Response({
                'count': total,
                'next': build_page_url(page_number + 1) if end < total else None,
                'previous': build_page_url(page_number - 1) if page_number > 1 else None,
                'typeCounts': type_counts,
                'results': page_items,
            })

        except Exception as e:
            logger.error(f"Error executing global search: {str(e)}")
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
        # Only return personas that have travel trajectories (place relationships)
        return Persona.objects.filter(p_x_l_pere__isnull=False).distinct()

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
        """Get summary of all trajectories for map overview"""
        # Get all unique places with trajectory counts
        places_with_trajectories = PersonaLugarRel.objects.select_related('lugar').values(
            'lugar__lugar_id', 'lugar__nombre_lugar', 'lugar__tipo', 'lugar__lat', 'lugar__lon'
        ).annotate(
            trajectory_count=Count('persona_x_lugares'),
            persona_count=Count('personas', distinct=True)
        ).filter(lugar__lat__isnull=False, lugar__lon__isnull=False)

        return Response({
            'total_places': places_with_trajectories.count(),
            'places': list(places_with_trajectories)
        })


# Utility Views
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
        'groups': [g.name for g in user.groups.all()]
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