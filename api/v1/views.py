import logging

from django.db.models import Q as DjangoQ
from rest_framework.permissions import BasePermission
from rest_framework import viewsets, filters, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, action
from elasticsearch_dsl import Search
from elasticsearch_dsl.query import MultiMatch, Q as ESQ
from urllib.parse import urlencode
from rest_framework.pagination import PageNumberPagination

from dbgestor.models import (Documento, PersonaEsclavizada, PersonaNoEsclavizada, Corporacion,
                             PersonaLugarRel, Lugar)

from dbgestor.documents import (
    DocumentoDocument,
    PersonaNoEsclavizadaDocument,
    PersonaEsclavizadaDocument,
    CorporacionDocument,
    LugarDocument,
)

from .serializers import (LogMessageSerializer, DocumentoSerializer, PersonaEsclavizadaSerializer, 
                          PersonaNoEsclavizadaSerializer, CorporacionSerializer, PersonaLugarRelSerializer,
                          LugarAmpliadoSerializer)


logger = logging.getLogger('dbgestor')

# Create your views here.
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
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

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
    pagination_class = PageNumberPagination

    def get_queryset(self):
        sort_by = self.request.query_params.get('sort', '')
        if sort_by:
            return PersonaEsclavizada.objects.all().order_by(sort_by)
        return PersonaEsclavizada.objects.all()
    
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
    search_fields = ['nombre_normalizado']
    filter_backends = (filters.SearchFilter,)
    serializer_class = PersonaNoEsclavizadaSerializer
    
    def get_queryset(self):
        sort_by = self.request.query_params.get('sort', '')
        if sort_by:
            return PersonaNoEsclavizada.objects.all().order_by(sort_by)
        return PersonaNoEsclavizada.objects.all()
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '')
        if query:
            results = PersonaNoEsclavizada.objects.filter(DjangoQ(nombre_normalizado__icontains=query))
            serializer = PersonaNoEsclavizadaSerializer(results, many=True)
            return Response(serializer.data)
        return Response({'error': 'No query provided'}, status=400)
    
class CorporacionViewSet(viewsets.ModelViewSet):
    permission_classes = [APIPerm]
    search_fields = ['nombre_institucion', 'tipo_institucion__tipo', 'personas_asociadas__nombre_normalizado', 'notas']
    filter_backends = (filters.SearchFilter,)
    serializer_class = CorporacionSerializer
    
    def get_queryset(self):
        sort_by = self.request.query_params.get('sort', '')
        if sort_by:
            return Corporacion.objects.all().order_by(sort_by)
        return Corporacion.objects.all()
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '')
        if query:
            results = Corporacion.objects.filter(DjangoQ(nombre_institucion__icontains=query) | DjangoQ(tipo_institucion__tipo__icontains=query) | DjangoQ(personas_asociadas__nombre_normalizado__icontains=query) | DjangoQ(notas__icontains=query))
            serializer = CorporacionSerializer(results, many=True)
            return Response(serializer.data)

class LugarAmpliadoViewSet(viewsets.ModelViewSet):
    permission_classes = [APIPerm]
    search_fields = ['nombre_lugar', 'tipo', 'otros_nombres', 'es_parte_de']
    filter_backends = (filters.SearchFilter,)
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
        if query:
            results = Lugar.objects.filter(DjangoQ(nombre_lugar__icontains=query) | DjangoQ(tipo__icontains=query) | DjangoQ(otros_nombres__icontains=query) | DjangoQ(es_parte_de__nombre_lugar__icontains=query))
            serializer = LugarAmpliadoSerializer(results, many=True)
            return Response(serializer.data)
        return Response({'error': 'No query provided'}, status=400)

      
class SearchAPIView(APIView):
    """
    Search API view to search for documents, personas, corporaciones, and places.
    """
    def get(self, request, *args, **kwargs):
        query = request.query_params.get('q', '')
        sort_by = request.query_params.get('sort', '_score')
        sort_order = request.query_params.get('order', 'desc')
        page_number = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        doc_type = request.query_params.get('type', None)

        if not query:
            return Response({'error': 'No query provided'}, status=400)

        # Define document classes and their search fields
        document_classes = {
            'documento': (DocumentoDocument, ['titulo', 'descripcion', 'documento_idno', 'notas']),
            'personanoesclavizada': (PersonaNoEsclavizadaDocument, ['nombre_normalizado', 'nombres', 'apellidos', 'persona_idno', 'entidad_asociada', 'honorifico', 'ocupaciones__actividad', 'notas']),
            'personaesclavizada': (PersonaEsclavizadaDocument, ['nombre_normalizado', 'nombres', 'apellidos', 'persona_idno', 'hispanizacion.hispanizacion', 'etnonimos.etonimo', 'procedencia.nombre_lugar', 'procedencia_adicional', 'ocupaciones__actividad', 'marcas_corporales', 'conducta', 'salud', 'notas']),
            'corporacion': (CorporacionDocument, ['nombre_institucion', 'tipo_institucion__tipo', 'personas_asociadas__nombre_normalizado', 'notas']),
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

        # Apply pagination
        start = (page_number - 1) * page_size
        search = search[start:start + page_size]

        # Execute search
        try:
            response = search.execute()
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
            'results': results,
        }

        return Response(response_data)
