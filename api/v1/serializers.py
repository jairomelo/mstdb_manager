from api.models import LogMessage
from rest_framework import serializers
from dbgestor.models import (Archivo, Documento, PersonaEsclavizada, PersonaNoEsclavizada, Corporacion, InstitucionRolEvento,
                             PersonaLugarRel, Lugar, PersonaRelaciones, PersonaLugarRel, Actividades, Persona,
                             PersonaRolEvento)

from django.db.models import Manager

from django_elasticsearch_dsl.registries import registry

class BaseElasticSearchSerializer(serializers.ModelSerializer):
    class Meta:
        abstract = True
        
    @classmethod
    def search(cls, query):
        """Search in ElasticSearch index"""
        document = registry.get_document(cls.Meta.model.__name__)
        results = document.search().query('multi_match', query=query, fields=['*'])
        return results.to_dict()

class LogMessageSerializer(BaseElasticSearchSerializer):
    level = serializers.CharField(max_length=10)
    message = serializers.CharField()
    
    class Meta:
        model = LogMessage
        fields = ['level', 'message']

class ArchivoSerializer(BaseElasticSearchSerializer):
    nombre_abreviado = serializers.CharField(read_only=True)
    archivo_idno = serializers.CharField(read_only=True)

    class Meta:
        model = Archivo
        fields = ['archivo_id', 'nombre', 'nombre_abreviado', 'archivo_idno', 'created_at', 'updated_at']

class DocumentoSerializer(BaseElasticSearchSerializer):
    archivo = ArchivoSerializer(read_only=True)
    tipo_documento = serializers.StringRelatedField()
    lugar_de_produccion = serializers.StringRelatedField()

    class Meta:
        model = Documento
        fields = ['documento_id', 'documento_idno', 'archivo', 'fondo', 'subfondo', 'serie', 'subserie',
                  'tipo_udc', 'unidad_documental_compuesta', 'tipo_documento', 'sigla_documento',
                  'titulo', 'descripcion', 'deteriorado', 'fecha_inicial', 'fecha_inicial_raw', 'fecha_final',
                  'fecha_final_raw', 'lugar_de_produccion', 'folio_inicial', 'folio_final', 'notas', 'created_at', 'updated_at']


class SimplePersonaSerializer(BaseElasticSearchSerializer):
    class Meta:
        model = PersonaEsclavizada
        fields = ['persona_id', 'persona_idno', 'nombre_normalizado', 'polymorphic_ctype']

class SimpleLugarSerializer(BaseElasticSearchSerializer):
    class Meta:
        model = Lugar
        fields = ['lugar_id', 'nombre_lugar', 'tipo']

class PersonaRelacionesSerializer(BaseElasticSearchSerializer):
    documento = DocumentoSerializer(read_only = True)
    personas = SimplePersonaSerializer(many=True, read_only=True)

    class Meta:
        model = PersonaRelaciones
        fields = ['persona_relacion_id', 'documento', 'personas', 'naturaleza_relacion', 'descripcion_relacion']

class PersonaLugarRelSerializer(BaseElasticSearchSerializer):
    documento = DocumentoSerializer(read_only=True)
    lugar = SimpleLugarSerializer(read_only=True)
    situacion_lugar = serializers.StringRelatedField()

    class Meta:
        model = PersonaLugarRel
        fields = ['persona_x_lugares', 'documento', 'lugar', 'situacion_lugar', 'ordinal']

class ActividadesSerializer(BaseElasticSearchSerializer):
    
    class Meta:
        model = Actividades
        fields = ['actividad']

class PersonaRolEventoSerializer(BaseElasticSearchSerializer):
    documento = DocumentoSerializer(read_only=True)
    rol_evento = serializers.CharField(source='rol_evento.rol_evento', read_only=True)
    personas = SimplePersonaSerializer(many=True, read_only=True)
    
    class Meta:
        model =  PersonaRolEvento
        fields = ['id', 'documento', 'personas', 'rol_evento']

class PersonaEsclavizadaSerializer(BaseElasticSearchSerializer):
    documentos = DocumentoSerializer(many=True, read_only=True)
    hispanizacion = serializers.SerializerMethodField()
    etnonimos = serializers.SerializerMethodField()
    ocupaciones = ActividadesSerializer(many=True, read_only=True)
    procedencia = serializers.SerializerMethodField()
    relaciones = PersonaRelacionesSerializer(many=True, read_only=True)
    lugares = PersonaLugarRelSerializer(source='p_x_l_pere', many=True, read_only=True)
    sexo = serializers.CharField(source='get_sexo_display', read_only=True)
    unidad_temporal_edad = serializers.CharField(source='get_unidad_temporal_edad_display', read_only=True)

    class Meta:
        model = PersonaEsclavizada
        fields = ['persona_id', 'persona_idno', 'nombre_normalizado', 'nombres', 'apellidos',
                  'sexo', 'edad', 'unidad_temporal_edad', 'altura', 'cabello', 'ojos',
                  'hispanizacion', 'etnonimos', 'ocupaciones',  'procedencia', 'procedencia_adicional',
                  'marcas_corporales', 'conducta', 'salud', 'documentos', 'created_at', 
                  'updated_at', 'polymorphic_ctype', 'relaciones', 'lugares']

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

class PersonaNoEsclavizadaSerializer(BaseElasticSearchSerializer):
    documentos = DocumentoSerializer(many=True, read_only=True)
    relaciones = PersonaRelacionesSerializer(many=True, read_only=True)
    lugares = PersonaLugarRelSerializer(source='p_x_l_pere', many=True, read_only=True)
    sexo = serializers.CharField(source='get_sexo_display', read_only=True)
    eventos = PersonaRolEventoSerializer(source='p_roles_evento', many=True, read_only=True)
    
    class Meta:
        model = PersonaNoEsclavizada
        fields = ['persona_id', 'persona_idno', 'nombre_normalizado', 'nombres', 'apellidos',
                  'sexo', 'entidad_asociada', 'honorifico', 'created_at', 'updated_at', 'documentos', 'relaciones', 'eventos',
                  'lugares', 'polymorphic_ctype']


class SimpleCorporacionSerializer(BaseElasticSearchSerializer):
    lugar_corporacion = SimpleLugarSerializer(read_only=True)
    class Meta:
        model = Corporacion
        fields = ['corporacion_id', 'nombre_institucion', 'tipo_institucion', 'lugar_corporacion']

class InstitucionRolEventoSerializer(BaseElasticSearchSerializer):
    documento = DocumentoSerializer(read_only=True)
    rol_evento = serializers.CharField(source='rol_evento.rol_evento', read_only=True)
    corporaciones = SimpleCorporacionSerializer(many=True, read_only=True)
    
    class Meta:
        model = InstitucionRolEvento
        fields = ['id', 'documento', 'corporaciones', 'rol_evento']

class CorporacionSerializer(BaseElasticSearchSerializer):
    documentos = DocumentoSerializer(many=True, read_only=True)
    personas_asociadas = SimplePersonaSerializer(many=True, read_only=True)
    tipo_institucion = serializers.CharField(source='get_tipo_institucion', read_only=True)
    eventos = InstitucionRolEventoSerializer(source='p_roles_evento', many=True, read_only=True)
    lugar_corporacion = SimpleLugarSerializer(read_only=True)

    class Meta:
        model = Corporacion
        fields = ['corporacion_id', 'nombre_institucion', 'tipo_institucion', 'lugar_corporacion',
                  'notas', 'created_at', 'updated_at', 'personas_asociadas', 'documentos',
                  'eventos']

class PersonaLugarRelSerializer(BaseElasticSearchSerializer):
    personas = SimplePersonaSerializer(many=True, read_only=True)
    lugar = SimpleLugarSerializer(read_only=True)
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
                'nombre_normalizado': persona.nombre_normalizado,
                'polymorphic_ctype': str(persona.polymorphic_ctype)
            } for persona in instance.personas.all()
        ]
        return representation

class LugarAmpliadoSerializer(BaseElasticSearchSerializer):
    personas_relacionadas = serializers.SerializerMethodField()
    personas_esclavizadas_procedencia = serializers.SerializerMethodField()
    
    class Meta:
        model = Lugar
        fields = ['lugar_id', 'nombre_lugar', 'tipo', 'otros_nombres', 'es_parte_de', 'lat', 'lon',
                  'personas_relacionadas', 'personas_esclavizadas_procedencia']

    def get_personas_relacionadas(self, obj):
        personas_lugar_rel = PersonaLugarRel.objects.filter(lugar=obj)
        return PersonaLugarRelSerializer(personas_lugar_rel, many=True).data


    def get_personas_esclavizadas_procedencia(self, obj):
        esclavizados = PersonaEsclavizada.objects.filter(procedencia=obj)
        return PersonaEsclavizadaSerializer(esclavizados, many=True).data
