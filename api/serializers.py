from rest_framework import serializers
from dbgestor.models import Archivo, Documento, PersonaEsclavizada, PersonaNoEsclavizada, Corporacion


class ArchivoSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Archivo
        fields = '__all__'

class DocumentoSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Documento
        fields = '__all__'
        
    
class PersonaEsclavizadaSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = PersonaEsclavizada
        fields = '__all__'
        
class PersonaNoEsclavizadaSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = PersonaNoEsclavizada
        fields = '__all__'

class CorporacionSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Corporacion
        fields = '__all__'
