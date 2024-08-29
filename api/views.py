from django.core.paginator import Paginator
from django.shortcuts import render
from django.db.models import Q
from rest_framework import generics, viewsets, filters
from rest_framework.views import APIView
from rest_framework.response import Response

from dbgestor.models import (Archivo, Documento, PersonaEsclavizada, PersonaNoEsclavizada, Corporacion,
                             PersonaLugarRel)
from .serializers import (ArchivoSerializer, DocumentoSerializer, PersonaEsclavizadaSerializer, 
                          PersonaNoEsclavizadaSerializer, CorporacionSerializer, PersonaLugarRelSerializer)

# Create your views here.

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
    
class SearchAPIView(APIView):
    """
    API view to handle search queries across multiple models with custom pagination.
    Supports exact phrase matching using quotes.
    """
    
    def get(self, request, *args, **kwargs):
        query = request.query_params.get('q', '')
        filter_type = request.query_params.get('filter', 'all')
        
        if query:
            # Check if the query is wrapped in quotes for exact phrase matching
            exact_match = False
            if query.startswith('"') and query.endswith('"'):
                exact_match = True
                query = query[1:-1]  # Remove the quotes
            
            # Perform search queries across all models
            documentos = Documento.objects.none()
            personas_no_esclavizadas = PersonaNoEsclavizada.objects.none()
            personas_esclavizadas = PersonaEsclavizada.objects.none()
            corporaciones = Corporacion.objects.none()
            personas_lugar_rel = PersonaLugarRel.objects.none()
            
            # Helper function to create Q objects based on exact match or contains
            def create_q(field):
                return Q(**{f"{field}__exact": query}) if exact_match else Q(**{f"{field}__icontains": query})
            
            # Apply filters based on filter type
            if filter_type == 'all' or filter_type == 'documentos':
                documentos = Documento.objects.filter(
                    create_q('titulo') | 
                    create_q('descripcion') |
                    create_q('documento_idno') |
                    create_q('fondo') |
                    create_q('subfondo') |
                    create_q('serie') |
                    create_q('subserie') |
                    create_q('unidad_documental_compuesta') |
                    create_q('sigla_documento') |
                    create_q('notas')
                )
            if filter_type == 'all' or filter_type == 'personas_no_esclavizadas':
                personas_no_esclavizadas = PersonaNoEsclavizada.objects.filter(
                    create_q('nombre_normalizado') | 
                    create_q('nombres') |
                    create_q('apellidos') |
                    create_q('persona_idno') |
                    create_q('entidad_asociada') |
                    create_q('honorifico') |
                    create_q('notas')
                )
            if filter_type == 'all' or filter_type == 'personas_esclavizadas':
                personas_esclavizadas = PersonaEsclavizada.objects.filter(
                    create_q('nombre_normalizado') | 
                    create_q('nombres') |
                    create_q('apellidos') |
                    create_q('persona_idno') |
                    create_q('hispanizacion__hispanizacion') |
                    create_q('etnonimos__etonimo') |
                    create_q('procedencia__nombre_lugar') |
                    create_q('procedencia_adicional') |
                    create_q('marcas_corporales') |
                    create_q('conducta') |
                    create_q('salud') |
                    create_q('notas')
                )
            if filter_type == 'all' or filter_type == 'corporaciones':
                corporaciones = Corporacion.objects.filter(
                    create_q('nombre_institucion') | 
                    create_q('tipo_institucion__tipo') |
                    create_q('personas_asociadas__nombre_normalizado') |
                    create_q('notas')
                )
            if filter_type == 'all' or filter_type == 'personas_lugar_rel':
                personas_lugar_rel = PersonaLugarRel.objects.filter(
                    create_q('personas__nombre_normalizado') | 
                    create_q('lugar__nombre_lugar') |
                    create_q('situacion_lugar__situacion') |
                    create_q('documento__titulo') |
                    create_q('notas')
                )
            
            # Serialize the results without pagination first
            serialized_data = (
                DocumentoSerializer(documentos, many=True).data +
                PersonaNoEsclavizadaSerializer(personas_no_esclavizadas, many=True).data +
                PersonaEsclavizadaSerializer(personas_esclavizadas, many=True).data +
                CorporacionSerializer(corporaciones, many=True).data +
                PersonaLugarRelSerializer(personas_lugar_rel, many=True).data
            )
            
            # Combine all serialized results into a single list
            combined_results = serialized_data
            
            # Paginate the combined results
            paginator = Paginator(combined_results, 20)  # Adjust page size as needed
            page_number = request.query_params.get('page', 1)
            paginated_data = paginator.get_page(page_number)
            
            # Construct the paginated response manually
            response_data = {
                'count': paginator.count,
                'next': paginated_data.has_next() and f'?page={paginated_data.next_page_number()}',
                'previous': paginated_data.has_previous() and f'?page={paginated_data.previous_page_number()}',
                'results': paginated_data.object_list,
            }
            
            return Response(response_data)
        
        return Response({'error': 'No query provided'}, status=400)