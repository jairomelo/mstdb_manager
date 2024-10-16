import logging

from django.core.paginator import Paginator
from django.shortcuts import render
from django.db.models import Q
from rest_framework.permissions import BasePermission
from rest_framework import generics, viewsets, filters, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, action
from django_elasticsearch_dsl.registries import registry
from elasticsearch_dsl import Q as ESQ
from rest_framework.pagination import PageNumberPagination

from dbgestor.models import (Archivo, Documento, PersonaEsclavizada, PersonaNoEsclavizada, Corporacion,
                             PersonaLugarRel, Lugar)

from dbgestor.models import (
    DocumentoDocument,
    PersonaNoEsclavizadaDocument,
    PersonaEsclavizadaDocument,
    CorporacionDocument,
    LugarDocument,
)

from .serializers import (LogMessageSerializer, ArchivoSerializer, DocumentoSerializer, PersonaEsclavizadaSerializer, 
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
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '')
        if query:
            results = Documento.objects.filter(Q(titulo__icontains=query) | Q(descripcion__icontains=query) | Q(documento_idno__icontains=query) | Q(notas__icontains=query))
            serializer = DocumentoSerializer(results, many=True)
            return Response(results)
        return Response({'error': 'No query provided'}, status=400)
    
class PersonaEsclavizadaViewSet(viewsets.ModelViewSet):
    permission_classes = [APIPerm]
    search_fields = ['nombre_normalizado']
    filter_backends = (filters.SearchFilter,)
    serializer_class = PersonaEsclavizadaSerializer

    def get_queryset(self):
        sort_by = self.request.query_params.get('sort', '')
        if sort_by:
            return PersonaEsclavizada.objects.all().order_by(sort_by)
        return PersonaEsclavizada.objects.all()
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '')
        if query:
            results = PersonaEsclavizada.objects.filter(Q(nombre_normalizado__icontains=query))
            serializer = PersonaEsclavizadaSerializer(results, many=True)
            return Response(serializer.data)
        return Response({'error': 'No query provided'}, status=400)
    
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
            results = PersonaNoEsclavizada.objects.filter(Q(nombre_normalizado__icontains=query))
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
            results = Corporacion.objects.filter(Q(nombre_institucion__icontains=query) | Q(tipo_institucion__tipo__icontains=query) | Q(personas_asociadas__nombre_normalizado__icontains=query) | Q(notas__icontains=query))
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
            results = Lugar.objects.filter(Q(nombre_lugar__icontains=query) | Q(tipo__icontains=query) | Q(otros_nombres__icontains=query) | Q(es_parte_de__nombre_lugar__icontains=query))
            serializer = LugarAmpliadoSerializer(results, many=True)
            return Response(serializer.data)
        return Response({'error': 'No query provided'}, status=400)

      
class SearchAPIView(APIView):
    def get(self, request, *args, **kwargs):
        query = request.query_params.get('q', '')
        sort_by = request.query_params.get('sort', '')
        page_number = request.query_params.get('page', 1)
        page_size = 20

        if not query:
            return Response({'error': 'No query provided'}, status=400)

        # Check if the query is wrapped in quotes for exact phrase matching
        exact_match = query.startswith('"') and query.endswith('"')
        if exact_match:
            query = query[1:-1]  # Remove the quotes

        # Define document classes to search over
        document_classes = [
            DocumentoDocument,
            PersonaNoEsclavizadaDocument,
            PersonaEsclavizadaDocument,
            CorporacionDocument,
            LugarDocument,
        ]

        # Define the fields to search on for each document class
        search_fields = {
            DocumentoDocument: ['titulo', 'descripcion', 'documento_idno', 'notas'],
            PersonaNoEsclavizadaDocument: ['nombre_normalizado', 'nombres', 'apellidos', 'persona_idno', 'entidad_asociada', 'honorifico', 'ocupaciones__actividad', 'notas'],
            PersonaEsclavizadaDocument: ['nombre_normalizado', 'nombres', 'apellidos', 'persona_idno', 'hispanizacion.hispanizacion', 'etnonimos.etonimo', 'procedencia.nombre_lugar', 'procedencia_adicional', 'ocupaciones__actividad', 'marcas_corporales', 'conducta', 'salud', 'notas'],
            CorporacionDocument: ['nombre_institucion', 'tipo_institucion__tipo', 'personas_asociadas__nombre_normalizado', 'notas'],
            LugarDocument: ['nombre_lugar', 'tipo', 'otros_nombres', 'es_parte_de__nombre_lugar'],
        }

        results = []

        # Iterate over each document class and perform the search
        for document_class in document_classes:
            q_objects = ESQ('multi_match', query=query, fields=search_fields[document_class], type='best_fields')

            # Execute the search using the document class
            try:
                search = document_class.search().query(q_objects)
                search = search.source(search_fields[document_class])

                if sort_by:
                    search = search.sort(sort_by)

                # Pagination
                page_size = int(page_size)
                start = (int(page_number) - 1) * page_size
                search = search[start:start + page_size]

                # Execute search
                response = search.execute()
                logger.debug(f"Elasticsearch response for {document_class.__name__}: {response.to_dict()}")

                # Add results to the list
                results.extend(response.hits.hits)

            except Exception as e:
                logger.error(f"Error executing search for {document_class.__name__}: {str(e)}")

        # Prepare the response data
        response_data = {
            'count': len(results),
            'results': [hit.to_dict() for hit in results],
        }

        return Response(response_data)