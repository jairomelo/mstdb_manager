from django.shortcuts import render
from rest_framework import generics, viewsets

from dbgestor.models import Documento
from .serializers import DocumentoSerializer

# Create your views here.

class DocumentoViewSet(viewsets.ModelViewSet):
    queryset = Documento.objects.all()
    serializer_class = DocumentoSerializer
