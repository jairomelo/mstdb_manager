import logging

from django.core.paginator import Paginator
from django.shortcuts import render
from django.db.models import Q
from rest_framework import generics, viewsets, filters, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view

from dbgestor.models import (Archivo, Documento, PersonaEsclavizada, PersonaNoEsclavizada, Corporacion,
                             PersonaLugarRel)
from .serializers import (LogMessageSerializer, ArchivoSerializer, DocumentoSerializer, PersonaEsclavizadaSerializer, 
                          PersonaNoEsclavizadaSerializer, CorporacionSerializer, PersonaLugarRelSerializer)


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

class DocumentoViewSet(viewsets.ModelViewSet):
    queryset = Documento.objects.all()
    serializer_class = DocumentoSerializer
    
class PersonaEsclavizadaViewSet(viewsets.ModelViewSet):
    search_fields = ['nombre_normalizado']
    filter_backends = (filters.SearchFilter,)
    serializer_class = PersonaEsclavizadaSerializer

    def get_queryset(self):
        sort_by = self.request.query_params.get('sort', '')
        if sort_by:
            return PersonaEsclavizada.objects.all().order_by(sort_by)
        return PersonaEsclavizada.objects.all()
    
class PersonaNoEsclavizadaViewSet(viewsets.ModelViewSet):
    search_fields = ['nombre_normalizado']
    filter_backends = (filters.SearchFilter,)
    serializer_class = PersonaNoEsclavizadaSerializer
    
    def get_queryset(self):
        sort_by = self.request.query_params.get('sort', '')
        if sort_by:
            return PersonaNoEsclavizada.objects.all().order_by(sort_by)
        return PersonaNoEsclavizada.objects.all()
      
class SearchAPIView(APIView):
    """
    API view to handle search queries across multiple models with custom pagination.
    Supports exact phrase matching using quotes and sorting documents by date.
    """
    
    def get(self, request, *args, **kwargs):
        query = request.query_params.get('q', '')
        filter_type = request.query_params.get('filter', 'all')
        sort_by = request.query_params.get('sort', '')
        page_number = request.query_params.get('page', 1)
        page_size = 20  # Adjust as needed
        
        if not query:
            return Response({'error': 'No query provided'}, status=400)

        # Check if the query is wrapped in quotes for exact phrase matching
        exact_match = query.startswith('"') and query.endswith('"')
        if exact_match:
            query = query[1:-1]  # Remove the quotes

        # Define model-specific search fields
        search_fields = {
            'documentos': ['titulo', 'descripcion', 'documento_idno', 'notas'],
            'personas_no_esclavizadas': ['nombre_normalizado', 'nombres', 'apellidos', 'persona_idno', 'entidad_asociada', 'honorifico', 'ocupaciones__actividad', 'notas'],
            'personas_esclavizadas': ['nombre_normalizado', 'nombres', 'apellidos', 'persona_idno', 'hispanizacion__hispanizacion', 'etnonimos__etonimo', 'procedencia__nombre_lugar', 'procedencia_adicional', 'ocupaciones__actividad', 'marcas_corporales', 'conducta', 'salud', 'notas'],
            'corporaciones': ['nombre_institucion', 'tipo_institucion__tipo', 'personas_asociadas__nombre_normalizado', 'notas'],
            'personas_lugar_rel': ['personas__nombre_normalizado', 'lugar__nombre_lugar', 'situacion_lugar__situacion', 'documento__titulo', 'notas']
        }

        # Helper function to create Q objects
        def create_q(field):
            return Q(**{f"{field}__exact": query}) if exact_match else Q(**{f"{field}__icontains": query})

        # Perform search queries across selected models
        results = []
        models_to_search = search_fields.keys() if filter_type == 'all' else [filter_type]
        
        for model_name in models_to_search:
            if model_name == 'documentos':
                model_class = Documento
                serializer_class = DocumentoSerializer
            elif model_name == 'personas_no_esclavizadas':
                model_class = PersonaNoEsclavizada
                serializer_class = PersonaNoEsclavizadaSerializer
            elif model_name == 'personas_esclavizadas':
                model_class = PersonaEsclavizada
                serializer_class = PersonaEsclavizadaSerializer
            elif model_name == 'corporaciones':
                model_class = Corporacion
                serializer_class = CorporacionSerializer
            elif model_name == 'personas_lugar_rel':
                model_class = PersonaLugarRel
                serializer_class = PersonaLugarRelSerializer
            else:
                continue  # Skip if model_name is not recognized
            
            q_objects = Q()
            for field in search_fields[model_name]:
                q_objects |= create_q(field)
            
            queryset = model_class.objects.filter(q_objects)
            
            if model_name == 'documentos' and sort_by in ['fecha_inicial', '-fecha_inicial', 'fecha_final', '-fecha_final']:
                queryset = queryset.order_by(sort_by)
            
            serialized_data = serializer_class(queryset, many=True).data
            results.extend(serialized_data)

        # Paginate the combined results
        paginator = Paginator(results, page_size)
        paginated_data = paginator.get_page(page_number)

        response_data = {
            'count': paginator.count,
            'next': paginated_data.has_next() and f'?q={query}&filter={filter_type}&sort={sort_by}&page={paginated_data.next_page_number()}',
            'previous': paginated_data.has_previous() and f'?q={query}&filter={filter_type}&sort={sort_by}&page={paginated_data.previous_page_number()}',
            'results': paginated_data.object_list,
        }

        return Response(response_data)