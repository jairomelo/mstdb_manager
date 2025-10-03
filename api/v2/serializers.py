from api.models import LogMessage
from rest_framework import serializers
from dbgestor.models import (Archivo, Documento, PersonaEsclavizada, PersonaNoEsclavizada, Corporacion, InstitucionRolEvento,
                             PersonaLugarRel, Lugar, PersonaRelaciones, Actividades, Persona,
                             PersonaRolEvento)

from django.db.models import Manager
from django_elasticsearch_dsl.registries import registry


class BaseElasticSearchSerializer(serializers.ModelSerializer):
    class Meta:
        abstract = True
        
    @classmethod
    def search(cls, query):
        pass  # Implement search functionality


# Reference Serializers - Lightweight for relationships
class ArchivoReferenceSerializer(BaseElasticSearchSerializer):
    """Minimal Archivo data for references"""
    
    class Meta:
        model = Archivo
        fields = ['archivo_id', 'nombre', 'archivo_idno']


class DocumentoReferenceSerializer(BaseElasticSearchSerializer):
    """Minimal Documento data for references"""
    
    class Meta:
        model = Documento
        fields = ['documento_id', 'documento_idno', 'titulo']


class PersonaReferenceSerializer(BaseElasticSearchSerializer):
    """Minimal Persona data for references"""
    
    class Meta:
        model = Persona
        fields = ['persona_id', 'persona_idno', 'nombre_normalizado', 'polymorphic_ctype']


class LugarReferenceSerializer(BaseElasticSearchSerializer):
    """Minimal Lugar data for references"""
    
    class Meta:
        model = Lugar
        fields = ['lugar_id', 'nombre_lugar', 'tipo']


class CorporacionReferenceSerializer(BaseElasticSearchSerializer):
    """Minimal Corporacion data for references"""
    
    class Meta:
        model = Corporacion
        fields = ['corporacion_id', 'nombre_institucion']


# List Serializers - For table views and lightweight listings
class ArchivoListSerializer(BaseElasticSearchSerializer):
    """Archivo data for list views"""
    nombre_abreviado = serializers.CharField(read_only=True)
    documento_count = serializers.SerializerMethodField()

    class Meta:
        model = Archivo
        fields = ['archivo_id', 'nombre', 'nombre_abreviado', 'archivo_idno', 'documento_count', 'created_at', 'updated_at']

    def get_documento_count(self, obj):
        return obj.documento_set.count()


class DocumentoListSerializer(BaseElasticSearchSerializer):
    """Documento data for list views"""
    archivo = ArchivoReferenceSerializer(read_only=True)
    tipo_documento = serializers.StringRelatedField()
    lugar_de_produccion_id = serializers.IntegerField(source='lugar_de_produccion.lugar_id', read_only=True)

    class Meta:
        model = Documento
        fields = ['documento_id', 'documento_idno', 'archivo', 'titulo', 'tipo_documento', 
                  'fecha_inicial', 'fecha_final', 'lugar_de_produccion_id', 'created_at', 'updated_at']


class PersonaListSerializer(BaseElasticSearchSerializer):
    """Base Persona list serializer"""
    sexo = serializers.CharField(source='get_sexo_display', read_only=True)
    documento_count = serializers.SerializerMethodField()

    class Meta:
        model = Persona
        fields = ['persona_id', 'persona_idno', 'nombre_normalizado', 'nombres', 'apellidos',
                  'sexo', 'polymorphic_ctype', 'documento_count', 'created_at', 'updated_at']

    def get_documento_count(self, obj):
        return obj.documentos.count()


class PersonaEsclavizadaListSerializer(PersonaListSerializer):
    """PersonaEsclavizada data for list views"""
    unidad_temporal_edad = serializers.CharField(source='get_unidad_temporal_edad_display', read_only=True)

    class Meta(PersonaListSerializer.Meta):
        model = PersonaEsclavizada
        fields = PersonaListSerializer.Meta.fields + ['edad', 'unidad_temporal_edad']


class PersonaNoEsclavizadaListSerializer(PersonaListSerializer):
    """PersonaNoEsclavizada data for list views"""

    class Meta(PersonaListSerializer.Meta):
        model = PersonaNoEsclavizada


class LugarListSerializer(BaseElasticSearchSerializer):
    """Lugar data for list views"""
    persona_count = serializers.SerializerMethodField()

    class Meta:
        model = Lugar
        fields = ['lugar_id', 'nombre_lugar', 'tipo', 'lat', 'lon', 'persona_count']

    def get_persona_count(self, obj):
        # Count personas through PersonaLugarRel intermediate model
        return Persona.objects.filter(p_x_l_pere__lugar=obj).distinct().count()


class CorporacionListSerializer(BaseElasticSearchSerializer):
    """Corporacion data for list views"""
    tipo_institucion = serializers.CharField(source='get_tipo_institucion', read_only=True)
    lugar_corporacion = LugarReferenceSerializer(read_only=True)

    class Meta:
        model = Corporacion
        fields = ['corporacion_id', 'nombre_institucion', 'tipo_institucion', 'lugar_corporacion']


# Detail Serializers - Full entity data with references instead of nested objects
class ArchivoDetailSerializer(BaseElasticSearchSerializer):
    """Full Archivo details"""
    nombre_abreviado = serializers.CharField(read_only=True)
    documento_ids = serializers.SerializerMethodField()

    class Meta:
        model = Archivo
        fields = ['archivo_id', 'nombre', 'nombre_abreviado', 'archivo_idno', 
                  'documento_ids', 'created_at', 'updated_at']

    def get_documento_ids(self, obj):
        return list(obj.documento_set.values_list('documento_id', flat=True))


class DocumentoDetailSerializer(BaseElasticSearchSerializer):
    """Full Documento details"""
    archivo = ArchivoReferenceSerializer(read_only=True)
    tipo_documento = serializers.StringRelatedField()
    lugar_de_produccion = LugarReferenceSerializer(read_only=True)
    persona_ids = serializers.SerializerMethodField()

    class Meta:
        model = Documento
        fields = ['documento_id', 'documento_idno', 'archivo', 'fondo', 'subfondo', 'serie', 'subserie',
                  'tipo_udc', 'unidad_documental_compuesta', 'tipo_documento', 'sigla_documento',
                  'titulo', 'descripcion', 'deteriorado', 'fecha_inicial', 'fecha_inicial_raw', 'fecha_final',
                  'fecha_final_raw', 'lugar_de_produccion', 'folio_inicial', 'folio_final', 'notas', 
                  'persona_ids', 'created_at', 'updated_at']

    def get_persona_ids(self, obj):
        return list(obj.persona_set.values_list('persona_id', flat=True))


class PersonaDetailSerializer(BaseElasticSearchSerializer):
    """Base Persona detail serializer"""
    sexo = serializers.CharField(source='get_sexo_display', read_only=True)
    documento_ids = serializers.SerializerMethodField()
    lugar_ids = serializers.SerializerMethodField()
    relacion_ids = serializers.SerializerMethodField()

    class Meta:
        model = Persona
        fields = ['persona_id', 'persona_idno', 'nombre_normalizado', 'nombres', 'apellidos',
                  'sexo', 'polymorphic_ctype', 'documento_ids', 'lugar_ids', 'relacion_ids',
                  'created_at', 'updated_at']

    def get_documento_ids(self, obj):
        return list(obj.documentos.values_list('documento_id', flat=True))

    def get_lugar_ids(self, obj):
        if hasattr(obj, 'p_x_l_pere'):
            return list(obj.p_x_l_pere.values_list('lugar_id', flat=True))
        return []

    def get_relacion_ids(self, obj):
        return list(obj.relaciones.values_list('persona_relacion_id', flat=True))


class PersonaEsclavizadaDetailSerializer(PersonaDetailSerializer):
    """Full PersonaEsclavizada details"""
    hispanizacion = serializers.SerializerMethodField()
    etnonimos = serializers.SerializerMethodField()
    procedencia = serializers.SerializerMethodField()
    ocupacion_ids = serializers.SerializerMethodField()
    unidad_temporal_edad = serializers.CharField(source='get_unidad_temporal_edad_display', read_only=True)

    class Meta(PersonaDetailSerializer.Meta):
        model = PersonaEsclavizada
        fields = PersonaDetailSerializer.Meta.fields + [
            'edad', 'unidad_temporal_edad', 'altura', 'cabello', 'ojos',
            'hispanizacion', 'etnonimos', 'ocupacion_ids', 'procedencia', 'procedencia_adicional',
            'marcas_corporales', 'conducta', 'salud'
        ]

    def get_hispanizacion(self, obj):
        return self.get_attribute_or_none(obj, 'hispanizacion')

    def get_etnonimos(self, obj):
        return self.get_attribute_or_none(obj, 'etnonimos')

    def get_procedencia(self, obj):
        return self.get_attribute_or_none(obj, 'procedencia')

    def get_ocupacion_ids(self, obj):
        return list(obj.ocupaciones.values_list('actividad_id', flat=True))

    def get_attribute_or_none(self, obj, attr):
        try:
            attribute = getattr(obj, attr)
            if hasattr(attribute, 'all'):
                return [str(item) for item in attribute.all()]
            return str(attribute) if attribute else None
        except:
            return None


class PersonaNoEsclavizadaDetailSerializer(PersonaDetailSerializer):
    """Full PersonaNoEsclavizada details"""
    evento_ids = serializers.SerializerMethodField()

    class Meta(PersonaDetailSerializer.Meta):
        model = PersonaNoEsclavizada
        fields = PersonaDetailSerializer.Meta.fields + ['evento_ids']

    def get_evento_ids(self, obj):
        if hasattr(obj, 'p_roles_evento'):
            return list(obj.p_roles_evento.values_list('id', flat=True))
        return []


class LugarDetailSerializer(BaseElasticSearchSerializer):
    """Full Lugar details"""
    persona_ids = serializers.SerializerMethodField()
    documento_ids = serializers.SerializerMethodField()

    class Meta:
        model = Lugar
        fields = ['lugar_id', 'nombre_lugar', 'tipo', 'lat', 'lon', 
                  'persona_ids', 'documento_ids']

    def get_persona_ids(self, obj):
        # Get personas through PersonaLugarRel intermediate model
        return list(Persona.objects.filter(p_x_l_pere__lugar=obj).distinct().values_list('persona_id', flat=True))

    def get_documento_ids(self, obj):
        # Get documents through PersonaLugarRel
        return list(obj.p_x_l_lugar.values_list('documento_id', flat=True).distinct())


class CorporacionDetailSerializer(BaseElasticSearchSerializer):
    """Full Corporacion details"""
    tipo_institucion_nombre = serializers.CharField(source='tipo_institucion.nombre', read_only=True)
    lugar_corporacion = LugarReferenceSerializer(read_only=True)
    documento_ids = serializers.SerializerMethodField()
    persona_ids = serializers.SerializerMethodField()
    evento_ids = serializers.SerializerMethodField()

    class Meta:
        model = Corporacion
        fields = ['corporacion_id', 'nombre_institucion', 'tipo_institucion_nombre', 'nombres_alternativos',
                  'lugar_corporacion', 'documento_ids', 'persona_ids', 'evento_ids']

    def get_documento_ids(self, obj):
        return list(obj.documentos.values_list('documento_id', flat=True))

    def get_persona_ids(self, obj):
        return list(obj.personas_asociadas.values_list('persona_id', flat=True))

    def get_evento_ids(self, obj):
        if hasattr(obj, 'roles_evento'):
            return list(obj.roles_evento.values_list('id', flat=True))
        return []


# Relationship Serializers - For handling M2M relationships
class PersonaRelacionesDetailSerializer(BaseElasticSearchSerializer):
    """PersonaRelaciones with references"""
    documento = DocumentoReferenceSerializer(read_only=True)
    persona_ids = serializers.SerializerMethodField()

    class Meta:
        model = PersonaRelaciones
        fields = ['persona_relacion_id', 'documento', 'persona_ids', 'naturaleza_relacion', 'descripcion_relacion']

    def get_persona_ids(self, obj):
        return list(obj.personas.values_list('persona_id', flat=True))


class PersonaLugarRelDetailSerializer(BaseElasticSearchSerializer):
    """PersonaLugarRel with references"""
    documento = DocumentoReferenceSerializer(read_only=True)
    lugar = LugarReferenceSerializer(read_only=True)
    persona_ids = serializers.SerializerMethodField()
    situacion_lugar = serializers.StringRelatedField()

    class Meta:
        model = PersonaLugarRel
        fields = ['persona_x_lugares', 'documento', 'lugar', 'persona_ids', 'situacion_lugar', 'ordinal']

    def get_persona_ids(self, obj):
        return list(obj.personas.values_list('persona_id', flat=True))


class PersonaRolEventoDetailSerializer(BaseElasticSearchSerializer):
    """PersonaRolEvento with references"""
    documento = DocumentoReferenceSerializer(read_only=True)
    rol_evento = serializers.CharField(source='rol_evento.rol_evento', read_only=True)
    persona_ids = serializers.SerializerMethodField()
    
    class Meta:
        model = PersonaRolEvento
        fields = ['id', 'documento', 'persona_ids', 'rol_evento']

    def get_persona_ids(self, obj):
        return list(obj.personas.values_list('persona_id', flat=True))


# Travel Trajectory Serializers - For map visualizations
class TravelTrajectorySerializer(BaseElasticSearchSerializer):
    """Lightweight travel trajectory data for map visualization"""
    persona = PersonaReferenceSerializer(read_only=True)
    lugar = LugarReferenceSerializer(read_only=True)
    documento = DocumentoReferenceSerializer(read_only=True)
    fecha_efectiva = serializers.SerializerMethodField()
    situacion_lugar = serializers.StringRelatedField()
    
    class Meta:
        model = PersonaLugarRel
        fields = ['persona_x_lugares', 'persona', 'lugar', 'documento', 'ordinal', 
                  'fecha_efectiva', 'situacion_lugar']

    def get_fecha_efectiva(self, obj):
        # Use fecha_inicial_lugar if available, otherwise fall back to documento.fecha_inicial
        return obj.fecha_inicial_lugar or (obj.documento.fecha_inicial if obj.documento else None)


class PersonaTravelTrajectorySerializer(serializers.Serializer):
    """Complete travel trajectory for a person - optimized for map visualization"""
    persona_id = serializers.IntegerField()
    persona_idno = serializers.CharField()
    nombre_normalizado = serializers.CharField()
    polymorphic_ctype = serializers.SerializerMethodField()
    trajectory_summary = serializers.SerializerMethodField()
    trajectory_points = serializers.SerializerMethodField()

    def get_polymorphic_ctype(self, obj):
        return str(obj.polymorphic_ctype)

    def get_trajectory_summary(self, obj):
        """Summary statistics for the trajectory"""
        lugares = obj.p_x_l_pere.all().order_by('ordinal')
        return {
            'total_locations': lugares.count(),
            'date_range': {
                'earliest': lugares.first().fecha_inicial_lugar or (lugares.first().documento.fecha_inicial if lugares.first() and lugares.first().documento else None),
                'latest': lugares.last().fecha_inicial_lugar or (lugares.last().documento.fecha_inicial if lugares.last() and lugares.last().documento else None)
            },
            'unique_places': lugares.values_list('lugar_id', flat=True).distinct().count()
        }

    def get_trajectory_points(self, obj):
        """Lightweight trajectory points for map rendering"""
        lugares = obj.p_x_l_pere.select_related('lugar', 'documento').all().order_by('ordinal')
        return [
            {
                'lugar_id': rel.lugar.lugar_id,
                'nombre_lugar': rel.lugar.nombre_lugar,
                'tipo_lugar': rel.lugar.tipo,
                'lat': float(rel.lugar.lat) if rel.lugar.lat else None,
                'lon': float(rel.lugar.lon) if rel.lugar.lon else None,
                'fecha': rel.fecha_inicial_lugar or (rel.documento.fecha_inicial if rel.documento else None),
                'ordinal': rel.ordinal,
                'situacion': str(rel.situacion_lugar) if rel.situacion_lugar else None,
                'documento_id': rel.documento.documento_id if rel.documento else None,
                'documento_titulo': rel.documento.titulo if rel.documento else None
            }
            for rel in lugares
        ]


# Simple utility serializers
class ActividadesSerializer(BaseElasticSearchSerializer):
    
    class Meta:
        model = Actividades
        fields = ['actividad_id', 'actividad']


class LogMessageSerializer(BaseElasticSearchSerializer):
    level = serializers.CharField(max_length=10)
    message = serializers.CharField()
    
    class Meta:
        model = LogMessage
        fields = ['level', 'message']


# History Serializers - For tracking changes using django-simple-history
class BaseHistorySerializer(serializers.ModelSerializer):
    """Base serializer for historical records"""
    history_user_name = serializers.SerializerMethodField()
    history_type_display = serializers.SerializerMethodField()
    
    def get_history_user_name(self, obj):
        """Get the username of the user who made the change"""
        return obj.history_user.username if obj.history_user else 'System'
    
    def get_history_type_display(self, obj):
        """Convert history type to human readable format"""
        type_mapping = {
            '+': 'Created',
            '~': 'Updated', 
            '-': 'Deleted'
        }
        return type_mapping.get(obj.history_type, obj.history_type)

    class Meta:
        abstract = True
        fields = ['history_id', 'history_date', 'history_user_name', 'history_type_display']


class DocumentoHistorySerializer(BaseHistorySerializer):
    """Documento history records"""
    
    class Meta:
        model = Documento.history.model  # This gets the HistoricalDocumento model
        fields = BaseHistorySerializer.Meta.fields + [
            'documento_id', 'documento_idno', 'titulo', 'fecha_inicial_raw',
            'fondo', 'subfondo', 'is_published'
        ]


class PersonaHistorySerializer(BaseHistorySerializer):
    """Persona history records"""
    
    class Meta:
        model = Persona.history.model  # This gets the HistoricalPersona model
        fields = BaseHistorySerializer.Meta.fields + [
            'persona_id', 'persona_idno', 'nombre_normalizado', 
            'nombres', 'apellidos', 'is_published'
        ]


class CorporacionHistorySerializer(BaseHistorySerializer):
    """Corporacion history records"""
    
    class Meta:
        model = Corporacion.history.model  # This gets the HistoricalCorporacion model
        fields = BaseHistorySerializer.Meta.fields + [
            'corporacion_id', 'nombre_institucion', 'nombres_alternativos', 'is_published'
        ]