import json
import logging

from django.db.models import Count, F
from django.db.models.functions import ExtractYear
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.http import JsonResponse
from django.middleware.csrf import get_token
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, action, permission_classes
from elasticsearch_dsl import Search
from elasticsearch_dsl.query import MultiMatch, Q as ESQ
from urllib.parse import urlencode
from rest_framework.pagination import PageNumberPagination

from dbgestor.models import (Documento, PersonaEsclavizada, PersonaNoEsclavizada, Corporacion,
                             PersonaLugarRel, Lugar, PersonaRelaciones, Persona)

from dbgestor.documents import (
    DocumentoDocument,
    PersonaNoEsclavizadaDocument,
    PersonaEsclavizadaDocument,
    CorporacionDocument,
    LugarDocument,
)

from .serializers import (LogMessageSerializer, DocumentoSerializer, PersonaEsclavizadaSerializer, 
                          PersonaNoEsclavizadaSerializer, CorporacionSerializer, PersonaLugarRelSerializer,
                          LugarAmpliadoSerializer, PersonaRelacionesSerializer, TravelTrajectorySerializer,
                          PersonaTravelTrajectorySerializer)


logger = logging.getLogger('dbgestor')

@ensure_csrf_cookie
def get_csrf_token(request):
    """
    Get CSRF token for the current session.
    """
    token = get_token(request)
    return JsonResponse({
        'csrfToken': token,
        'detail': 'CSRF cookie set'
    })

# user auth manager
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def whoami(request):
    """
    Return the current user.
    """
    user = request.user
    if user.is_authenticated:
        return Response({
            'username': user.username,
            'email': user.email,
            'is_staff': user.is_staff,
            'groups': [group.name for group in user.groups.all()]
        })
    else:
        return Response({'error': 'User not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)

def api_login(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user = authenticate(
            request,
            username=data["username"],
            password=data["password"]
        )
        if user is not None:
            login(request, user)
            return JsonResponse({
                "username": user.username,
                "email": user.email,
                "is_staff": user.is_staff
            })
        else:
            return JsonResponse({"error": "Invalid credentials"}, status=401)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    logout(request)
    return Response({"success": "Logged out successfully"}, status=200)

# Create your views here.

@api_view(['GET'])
def gender_status_distribution(request):
    data = (
        PersonaEsclavizada.objects.values('sexo', 'hispanizacion__hispanizacion').annotate(count=Count('persona_idno')).order_by('-count')
    )
    return Response(data)


@api_view(['POST'])
def log_message(request):
    try:
        serializer = LogMessageSerializer(data=request.data)
        if serializer.is_valid():
            level = serializer.validated_data['level'].upper()
            message = serializer.validated_data['message']
            
            log_method = getattr(logger, level.lower(), logger.info)
            log_method(f"Client log: {message}")
            
            return Response({'status': 'success'})
        else:
            logger.error(f"Invalid log data received: {serializer.errors}")
            return Response({'status': 'error', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception(f"Error processing log message: {str(e)}")
        return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class APIPerm(BasePermission):
    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        return request.user and (request.user.is_staff or request.user.groups.filter(name="colectores").exists())

class CustomPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'length'
    max_page_size = 100
    page_query_param = 'start'

class DocumentoViewSet(viewsets.ModelViewSet):
    permission_classes = [APIPerm]
    queryset = Documento.objects.all()
    serializer_class = DocumentoSerializer
    pagination_class = PageNumberPagination
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '')
        if not query:
            return Response({'error': 'No query provided'}, status=400)

        try:
            search = DocumentoDocument.search()
            fields = ['titulo', 'descripcion', 'documento_idno', 'notas']
            multi_match = MultiMatch(query=query, fields=fields, type="best_fields", fuzziness="AUTO")
            search = search.query(multi_match)
            
            page = self.paginate_queryset(search)
            
            if page is not None:
                response = search[page.start:page.end].execute()
                results = [hit.to_dict() for hit in response.hits]
                return self.get_paginated_response(results)
            
            response = search.execute()
            results = [hit.to_dict() for hit in response.hits]
            
            return Response(results)
        except Exception as e:
            logger.error(f"Error executing search: {str(e)}")
            return Response({'error': 'An error occurred during the search'}, status=500)


class PersonaEsclavizadaViewSet(viewsets.ModelViewSet):
    permission_classes = [APIPerm]
    serializer_class = PersonaEsclavizadaSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        queryset = PersonaEsclavizada.objects.all()        
        
        sort_by = self.request.query_params.get('sort_by', None)
        
        if sort_by:
            try:
                sort_params = json.loads(sort_by)
                ordering = []
                
                for param in sort_params:
                    column = param.get('column')
                    direction = param.get('dir')
                    
                    if column and direction:
                        ordering.append(
                            f"-{column}" if direction == 'desc' else column
                        )
                if ordering:
                    queryset = queryset.order_by(*ordering)
                    
            except json.JSONDecodeError:
                logger.error(f"Error sorting queryset: {sort_by}")
                pass
        return queryset
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '')
        if not query:
            return Response({'error': 'No query provided'}, status=400)

        try:
            search = PersonaEsclavizadaDocument.search()
            fields = ['nombre_normalizado', 'nombres', 'apellidos', 'persona_idno', 'hispanizacion.hispanizacion', 'etnonimos.etonimo', 'procedencia.nombre_lugar', 'procedencia_adicional', 'ocupaciones__actividad', 'marcas_corporales', 'conducta', 'salud', 'notas']
            multi_match = MultiMatch(query=query, fields=fields, type="best_fields", fuzziness="AUTO")
            search = search.query(multi_match)
            
            # Get the paginator
            paginator = self.pagination_class()
            page_size = paginator.get_page_size(request)
            
            # Execute search
            response = search[:page_size].execute()
            
            # Paginate the results
            page = paginator.paginate_queryset(response, request)
            
            if page is not None:
                results = [hit.to_dict() for hit in page]
                return paginator.get_paginated_response(results)
            
            # If pagination is not applied, return all results
            results = [hit.to_dict() for hit in response]
            
            return Response(results)
        except Exception as e:
            logger.error(f"Error executing search: {str(e)}")
            return Response({'error': 'An error occurred during the search'}, status=500)
    
class PersonaNoEsclavizadaViewSet(viewsets.ModelViewSet):
    permission_classes = [APIPerm]
    serializer_class = PersonaNoEsclavizadaSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        sort_by = self.request.query_params.get('sort', '')
        if sort_by:
            return PersonaNoEsclavizada.objects.all().order_by(sort_by)
        return PersonaNoEsclavizada.objects.all()
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '')
        if not query:
            return Response({'error': 'No query provided'}, status=400)

        try:
            search = PersonaNoEsclavizadaDocument.search()
            fields = ['nombre_normalizado', 'nombres', 'apellidos', 'persona_idno', 'entidad_asociada', 'honorifico', 'ocupaciones__actividad', 'notas']
            multi_match = MultiMatch(query=query, fields=fields, type="best_fields", fuzziness="AUTO")
            search = search.query(multi_match)
            
            # Get the paginator
            paginator = self.pagination_class()
            page_size = paginator.get_page_size(request)
            
            # Execute search
            response = search[:page_size].execute()
            
            # Paginate the results
            page = paginator.paginate_queryset(response, request)
            
            if page is not None:
                results = [hit.to_dict() for hit in page]
                return paginator.get_paginated_response(results)
            
            # If pagination is not applied, return all results
            results = [hit.to_dict() for hit in response]
            
            return Response(results)
        except Exception as e:
            logger.error(f"Error executing search: {str(e)}")
            return Response({'error': 'An error occurred during the search'}, status=500)
    
class CorporacionViewSet(viewsets.ModelViewSet):
    permission_classes = [APIPerm]
    serializer_class = CorporacionSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        sort_by = self.request.query_params.get('sort', '')
        if sort_by:
            return Corporacion.objects.all().order_by(sort_by)
        return Corporacion.objects.all()
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '')
        if not query:
            return Response({'error': 'No query provided'}, status=400)

        try:
            search = CorporacionDocument.search()
            fields = ['nombre_institucion', 'tipo_institucion.tipo', 'personas_asociadas.nombre_normalizado', 'lugar_corporacion.nombre_lugar', 'notas']
            multi_match = MultiMatch(query=query, fields=fields, type="best_fields", fuzziness="AUTO")
            search = search.query(multi_match)
            
            # Get the paginator
            paginator = self.pagination_class()
            page_size = paginator.get_page_size(request)
            
            # Execute search
            response = search[:page_size].execute()
            
            # Paginate the results
            page = paginator.paginate_queryset(response, request)
            
            if page is not None:
                results = [hit.to_dict() for hit in page]
                return paginator.get_paginated_response(results)
            
            # If pagination is not applied, return all results
            results = [hit.to_dict() for hit in response]
            
            return Response(results)
        except Exception as e:
            logger.error(f"Error executing search: {str(e)}")
            return Response({'error': 'An error occurred during the search'}, status=500)

class LugarAmpliadoViewSet(viewsets.ModelViewSet):
    permission_classes = [APIPerm]
    serializer_class = LugarAmpliadoSerializer
    pagination_class = CustomPagination
    
    def get_queryset(self):
        return Lugar.objects.all()
    
    @action(detail=True, methods=['get'])
    def personas_relacionadas(self, request, pk=None):
        lugar = self.get_object()
        personas_lugar_rel = PersonaLugarRel.objects.filter(lugar=lugar)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(personas_lugar_rel, request)
        if page is not None:
            serializer = PersonaLugarRelSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = PersonaLugarRelSerializer(personas_lugar_rel, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '')
        if not query:
            return Response({'error': 'No query provided'}, status=400)

        try:
            search = LugarDocument.search()
            fields = ['nombre_lugar', 'tipo', 'otros_nombres', 'es_parte_de.nombre_lugar']
            multi_match = MultiMatch(query=query, fields=fields, type="best_fields", fuzziness="AUTO")
            search = search.query(multi_match)
            
            # Get the paginator
            paginator = self.pagination_class()
            page_size = paginator.get_page_size(request)
            
            # Execute search
            response = search[:page_size].execute()
            
            # Paginate the results
            page = paginator.paginate_queryset(response, request)
            
            if page is not None:
                results = [hit.to_dict() for hit in page]
                return paginator.get_paginated_response(results)
            
            # If pagination is not applied, return all results
            results = [hit.to_dict() for hit in response]
            
            return Response(results)
        except Exception as e:
            logger.error(f"Error executing search: {str(e)}")
            return Response({'error': 'An error occurred during the search'}, status=500)


class PersonaLugarRelViewSet(viewsets.ModelViewSet):
    permission_classes = [APIPerm]
    serializer_class = PersonaLugarRelSerializer
    pagination_class = CustomPagination
    
    def get_queryset(self):
        return PersonaLugarRel.objects.all().order_by('created_at')


class PersonaPersonaRelViewSet(viewsets.ModelViewSet):
    permission_classes = [APIPerm]
    serializer_class = PersonaRelacionesSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        return PersonaRelaciones.objects.all().order_by('naturaleza_relacion')

class SearchAPIView(APIView):
    """
    Search API view to search for documents, personas, corporaciones, and places.
    """
    def get(self, request, *args, **kwargs):
        query = request.query_params.get('q', '')
        
        if not query:
            return Response({'error': 'No query provided'}, status=400)
        
        sort_by = request.query_params.get('sort', '_score')
        
        if not sort_by.strip():
            sort_by = '_score'
            
        sort_order = request.query_params.get('order', 'desc')
        page_number = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        doc_type = request.query_params.get('type', None)


        # Define document classes and their search fields
        document_classes = {
            'documento': (DocumentoDocument, ['titulo', 'descripcion', 'documento_idno', 'notas']),
            'personanoesclavizada': (PersonaNoEsclavizadaDocument, ['nombre_normalizado', 'nombres', 'apellidos', 'persona_idno', 'entidad_asociada', 'honorifico', 'ocupaciones__actividad', 'notas']),
            'personaesclavizada': (PersonaEsclavizadaDocument, ['nombre_normalizado', 'nombres', 'apellidos', 'persona_idno', 'hispanizacion.hispanizacion', 'etnonimos.etonimo', 'procedencia.nombre_lugar', 'procedencia_adicional', 'ocupaciones__actividad', 'marcas_corporales', 'conducta', 'salud', 'notas']),
            'corporacion': (CorporacionDocument, ['nombre_institucion', 'tipo_institucion__tipo', 'personas_asociadas__nombre_normalizado', 'lugar_corporacion.nombre_lugar', 'notas']),
            'lugar': (LugarDocument, ['nombre_lugar', 'tipo', 'otros_nombres', 'es_parte_de__nombre_lugar']),
        }

        search = Search(index=[doc_class._index._name for doc_class, _ in document_classes.values()])

        filters = []

        if doc_type:
            doc_types = doc_type.split(',')
            type_filters = [ESQ('term', _index=document_classes[dt][0]._index._name) for dt in doc_types if dt in document_classes]
            if type_filters:
                filters.append(ESQ('bool', should=type_filters, minimum_should_match=1))

        # Add filters here as needed
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        if date_from or date_to:
            date_range_filter = []
            if date_from:
                date_range_filter.append(ESQ('range', fecha_inicial={'gte': date_from}))
                date_range_filter.append(ESQ('range', fecha_final={'gte': date_from}))
            if date_to:
                date_range_filter.append(ESQ('range', fecha_inicial={'lte': date_to}))
                date_range_filter.append(ESQ('range', fecha_final={'lte': date_to}))
            
            date_filter = ESQ('bool', must=date_range_filter)
            filters.append(date_filter)

        # Apply all filters
        if filters:
            search = search.filter('bool', must=filters)

        # Construct the query
        should_queries = []
        for doc_class, fields in document_classes.values():
            if query.startswith('"') and query.endswith('"') and len(query) > 2:
                exact_query = query.strip('"')
                should_queries.append(
                    MultiMatch(
                        query=exact_query,
                        fields=fields,
                        type="phrase",
                        boost=2.0
                    )
                )
            else:
                should_queries.append(
                    MultiMatch(
                        query=query,
                        fields=fields,
                        type="best_fields",
                        fuzziness="AUTO"
                    )
                )
        search = search.query(ESQ("bool", should=should_queries))

        # Add highlighting
        search = search.highlight_options(pre_tags=['<em>'], post_tags=['</em>'])
        search = search.highlight('*')

        # Apply sorting
        if sort_by != '_score':
            if sort_order not in ['asc', 'desc']:
                sort_order = 'desc'
            search = search.sort({sort_by: {'order': sort_order}})

        # Add aggregation for type counts
        search.aggs.bucket('type_counts', 'terms', field='_index')

        # Apply pagination
        start = (page_number - 1) * page_size
        search = search[start:start + page_size]
        

        # Execute search
        try:
            response = search.execute()
            
            index_to_type = {
            doc_class._index._name: type_name
                for type_name, (doc_class, _) in document_classes.items()
            }
            
            type_counts = {}
            if hasattr(response, 'aggregations') and hasattr(response.aggregations, 'type_counts'):
                for bucket in response.aggregations.type_counts.buckets:
                    type_name = index_to_type.get(bucket.key, bucket.key)
                    type_counts[type_name] = bucket.doc_count
            else:
                logger.warning("No type counts found in the response")
        except Exception as e:
            logger.error(f"Error executing search: {str(e)}")
            return Response({'error': 'An error occurred during the search'}, status=500)

        # Prepare the response data
        results = []
        for hit in response.hits:
            result = {
                'id': hit.meta.id,
                'type': hit.meta.index,
                'score': hit.meta.score,
                'highlight': hit.meta.highlight.to_dict() if hasattr(hit.meta, 'highlight') else {},
                'source': hit.to_dict()
            }
            results.append(result)

        # Prepare pagination links
        query_params = request.query_params.copy()

        def get_paginated_url(page):
            """
            Get the URL for a paginated page.
            """
            query_params['page'] = page
            return f"?{urlencode(query_params)}"

        response_data = {
            'count': response.hits.total.value,
            'page': page_number,
            'page_size': page_size,
            'next': get_paginated_url(page_number + 1) if response.hits.total.value > page_number * page_size else None,
            'previous': get_paginated_url(page_number - 1) if page_number > 1 else None,
            'typeCounts': type_counts,
            'results': results,
        }

        return Response(response_data)

class PlacesPeopleDistribution(APIView):
    def get(self, request):
        # Query and aggregate data grouped strictly by lugar, tipo, and year
        data = (
            PersonaEsclavizada.objects
            .annotate(
                year=ExtractYear('p_x_l_pere__documento__fecha_inicial'),
                lugar=F('p_x_l_pere__lugar__nombre_lugar'),
                tipo=F('p_x_l_pere__lugar__tipo'),
            )
            .values('lugar', 'tipo', 'year')  # Explicit grouping only by these fields
            .annotate(
                count=Count('persona_id', distinct=True)  # Count unique personas
            )
            .filter(lugar__isnull=False, year__isnull=False)
            .order_by('year', 'lugar')
        )

        # Transform the data for the response
        response_data = [
            {
                "lugar": item['lugar'],
                "tipo": item['tipo'],
                "year": item['year'],
                "count": item['count'],
            }
            for item in data
        ]

        return Response(response_data)

class PersonaTravelTrajectoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [APIPerm]
    serializer_class = PersonaTravelTrajectorySerializer
    pagination_class = CustomPagination
    
    def get_queryset(self):
        return Persona.objects.prefetch_related(
            'p_x_l_pere',
            'p_x_l_pere__lugar',
            'p_x_l_pere__documento',
            'p_x_l_pere__situacion_lugar'
        ).filter(
            p_x_l_pere__isnull=False
        ).distinct()

    @action(detail=True, methods=['get'])
    def trajectories(self, request, pk=None):
        persona = self.get_object()
        trajectories = persona.p_x_l_pere.all().select_related(
            'lugar',
            'documento',
            'situacion_lugar'
        ).order_by('ordinal')
        
        serializer = TravelTrajectorySerializer(trajectories, many=True)
        return Response(serializer.data)