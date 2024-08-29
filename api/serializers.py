from rest_framework import serializers
from dbgestor.models import (Archivo, Documento, PersonaEsclavizada, PersonaNoEsclavizada, Corporacion,
                             PersonaLugarRel)
from django.db.models import Manager

class ArchivoSerializer(serializers.ModelSerializer):
    nombre_abreviado = serializers.CharField(read_only=True)
    archivo_idno = serializers.CharField(read_only=True)

    class Meta:
        model = Archivo
        fields = ['archivo_id', 'nombre', 'nombre_abreviado', 'archivo_idno', 'created_at', 'updated_at']

class DocumentoSerializer(serializers.ModelSerializer):
    archivo = ArchivoSerializer(read_only=True)
    tipo_documento = serializers.StringRelatedField()
    lugar_de_produccion = serializers.StringRelatedField()

    class Meta:
        model = Documento
        fields = ['documento_id', 'documento_idno', 'archivo', 'fondo', 'subfondo', 'serie', 'subserie',
                  'tipo_udc', 'unidad_documental_compuesta', 'tipo_documento', 'sigla_documento',
                  'titulo', 'descripcion', 'deteriorado', 'fecha_inicial', 'fecha_inicial_raw', 'fecha_final',
                  'fecha_final_raw', 'lugar_de_produccion', 'folio_inicial', 'folio_final', 'notas', 'created_at', 'updated_at']

class PersonaEsclavizadaSerializer(serializers.ModelSerializer):
    hispanizacion = serializers.SerializerMethodField()
    etnonimos = serializers.SerializerMethodField()
    procedencia = serializers.SerializerMethodField()

    class Meta:
        model = PersonaEsclavizada
        fields = ['persona_id', 'persona_idno', 'nombre_normalizado', 'nombres', 'apellidos',
                  'sexo', 'edad', 'unidad_temporal_edad', 'altura', 'cabello', 'ojos',
                  'hispanizacion', 'etnonimos', 'procedencia', 'procedencia_adicional',
                  'marcas_corporales', 'conducta', 'salud', 'created_at', 'updated_at', 'polymorphic_ctype']

    def get_hispanizacion(self, obj):
        return self.get_attribute_or_none(obj, 'hispanizacion')

    def get_etnonimos(self, obj):
        return self.get_attribute_or_none(obj, 'etnonimos')

    def get_procedencia(self, obj):
        return self.get_attribute_or_none(obj, 'procedencia')

    def get_attribute_or_none(self, obj, attr):
        if hasattr(obj, attr):
            value = getattr(obj, attr)
            if isinstance(value, Manager):
                return [str(item) for item in value.all()]
            return str(value) if value else None
        return None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        return {k: v for k, v in representation.items() if v is not None}

class PersonaNoEsclavizadaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonaNoEsclavizada
        fields = ['persona_id', 'persona_idno', 'nombre_normalizado', 'nombres', 'apellidos',
                  'sexo', 'entidad_asociada', 'honorifico', 'created_at', 'updated_at', 'polymorphic_ctype']

class CorporacionSerializer(serializers.ModelSerializer):
    personas_asociadas = PersonaNoEsclavizadaSerializer(many=True, read_only=True)

    class Meta:
        model = Corporacion
        fields = ['corporacion_id', 'nombre_institucion', 'tipo_institucion', 'personas_asociadas',
                  'created_at', 'updated_at']

class PersonaLugarRelSerializer(serializers.ModelSerializer):
    personas = PersonaEsclavizadaSerializer(many=True, read_only=True)
    lugar = serializers.StringRelatedField()
    situacion_lugar = serializers.StringRelatedField()
    documento = DocumentoSerializer(read_only=True)

    class Meta:
        model = PersonaLugarRel
        fields = ['persona_x_lugares', 'documento', 'personas', 'lugar', 'situacion_lugar',
                  'ordinal', 'fecha_inicial_lugar', 'fecha_inicial_lugar_raw',
                  'fecha_inicial_lugar_factual', 'fecha_final_lugar', 'fecha_final_lugar_raw',
                  'fecha_final_lugar_factual', 'notas', 'created_at', 'updated_at']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['personas'] = [
            {
                'persona_id': persona.persona_id,
                'persona_idno': persona.persona_idno,
                'nombre_normalizado': persona.nombre_normalizado
            } for persona in instance.personas.all()
        ]
        return representation
