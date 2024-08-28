from django.core.paginator import Paginator
from django.shortcuts import render
from django.db.models import Q
from rest_framework import generics, viewsets, filters
from rest_framework.views import APIView
from rest_framework.response import Response

from dbgestor.models import (Archivo, Documento, PersonaEsclavizada, PersonaNoEsclavizada, Corporacion)
from .serializers import (ArchivoSerializer, DocumentoSerializer, PersonaEsclavizadaSerializer, 
                          PersonaNoEsclavizadaSerializer, CorporacionSerializer)

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
    """
    
    def get(self, request, *args, **kwargs):
        query = request.query_params.get('q', '')
        filter_type = request.query_params.get('filter', 'all')
        
        if query:
            # Perform search queries across all models
            documentos = Documento.objects.none()
            personas_no_esclavizadas = PersonaNoEsclavizada.objects.none()
            personas_esclavizadas = PersonaEsclavizada.objects.none()
            corporaciones = Corporacion.objects.none()
            
            # Apply filters based on filter type
            if filter_type == 'all' or filter_type == 'documentos':
                documentos = Documento.objects.filter(Q(titulo__icontains=query) | Q(descripcion__icontains=query))
            if filter_type == 'all' or filter_type == 'personas_no_esclavizadas':
                personas_no_esclavizadas = PersonaNoEsclavizada.objects.filter(Q(nombre_normalizado__icontains=query) | Q(notas__icontains=query))
            if filter_type == 'all' or filter_type == 'personas_esclavizadas':
                personas_esclavizadas = PersonaEsclavizada.objects.filter(Q(nombre_normalizado__icontains=query) | Q(notas__icontains=query))
            if filter_type == 'all' or filter_type == 'corporaciones':
                corporaciones = Corporacion.objects.filter(Q(nombre_institucion__icontains=query) | Q(personas_asociadas__nombre_normalizado__icontains=query))
            
            # Serialize the results without pagination first
            serialized_data = (
                DocumentoSerializer(documentos, many=True).data +
                PersonaNoEsclavizadaSerializer(personas_no_esclavizadas, many=True).data +
                PersonaEsclavizadaSerializer(personas_esclavizadas, many=True).data +
                CorporacionSerializer(corporaciones, many=True).data
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
