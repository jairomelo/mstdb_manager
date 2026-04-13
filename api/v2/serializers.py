import re
from datetime import datetime

from api.models import LogMessage
from rest_framework import serializers
from dbgestor.models import (Archivo, Documento, PersonaEsclavizada, PersonaNoEsclavizada, Corporacion, InstitucionRolEvento,
                             PersonaLugarRel, Lugar, PersonaRelaciones, Actividades, Persona,
                             PersonaRolEvento, Calidades, Hispanizaciones, Etonimos, EstadoCivil,
                             SituacionLugar, TipoDocumental, RolEvento, TiposInstitucion)

from django.db.models import Manager, Q


# Reference Serializers - Lightweight for relationships
class ArchivoReferenceSerializer(serializers.ModelSerializer):
    """Minimal Archivo data for references"""
    
    class Meta:
        model = Archivo
        fields = ['archivo_id', 'nombre', 'archivo_idno']


class DocumentoReferenceSerializer(serializers.ModelSerializer):
    """Minimal Documento data for references"""
    
    class Meta:
        model = Documento
        fields = ['documento_id', 'documento_idno', 'titulo']


class PersonaReferenceSerializer(serializers.ModelSerializer):
    """Minimal Persona data for references"""
    
    class Meta:
        model = Persona
        fields = ['persona_id', 'persona_idno', 'nombre_normalizado', 'polymorphic_ctype']


class LugarReferenceSerializer(serializers.ModelSerializer):
    """Minimal Lugar data for references"""
    
    class Meta:
        model = Lugar
        fields = ['lugar_id', 'nombre_lugar', 'tipo']


class CorporacionReferenceSerializer(serializers.ModelSerializer):
    """Minimal Corporacion data for references"""
    
    class Meta:
        model = Corporacion
        fields = ['corporacion_id', 'nombre_institucion']


# List Serializers - For table views and lightweight listings
class ArchivoListSerializer(serializers.ModelSerializer):
    """Archivo data for list views"""
    nombre_abreviado = serializers.CharField(read_only=True)
    documento_count = serializers.SerializerMethodField()

    class Meta:
        model = Archivo
        fields = ['archivo_id', 'nombre', 'nombre_abreviado', 'archivo_idno', 'documento_count', 'created_at', 'updated_at']

    def get_documento_count(self, obj):
        return obj.documento_set.count()


class DocumentoListSerializer(serializers.ModelSerializer):
    """Documento data for list views"""
    archivo = ArchivoReferenceSerializer(read_only=True)
    tipo_documento = serializers.StringRelatedField()
    lugar_de_produccion_id = serializers.IntegerField(source='lugar_de_produccion.lugar_id', read_only=True)

    class Meta:
        model = Documento
        fields = ['documento_id', 'documento_idno', 'archivo', 'titulo', 'tipo_documento', 
                  'fecha_inicial', 'fecha_final', 'lugar_de_produccion_id', 'created_at', 'updated_at']


class PersonaListSerializer(serializers.ModelSerializer):
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
    etnonimos = serializers.SerializerMethodField()
    hispanizacion = serializers.SerializerMethodField()
    has_relaciones = serializers.SerializerMethodField()
    has_lugares = serializers.SerializerMethodField()
    documento_list = serializers.SerializerMethodField()
    calidades = serializers.SerializerMethodField()
    fecha_nacimiento = serializers.DateField(read_only=True)
    earliest_doc_date = serializers.DateField(read_only=True)
    latest_doc_date = serializers.DateField(read_only=True)
    documented_span = serializers.SerializerMethodField()

    class Meta(PersonaListSerializer.Meta):
        model = PersonaEsclavizada
        fields = PersonaListSerializer.Meta.fields + [
            'edad', 'unidad_temporal_edad',
            'etnonimos', 'hispanizacion', 'calidades',
            'has_relaciones', 'has_lugares', 'documento_list',
            'fecha_nacimiento', 'earliest_doc_date', 'latest_doc_date', 'documented_span',
        ]

    def get_etnonimos(self, obj):
        return [str(e) for e in obj.etnonimos.all()]

    def get_hispanizacion(self, obj):
        return [str(h) for h in obj.hispanizacion.all()]

    def get_has_relaciones(self, obj):
        return obj.relaciones.exists()

    def get_has_lugares(self, obj):
        return obj.p_x_l_pere.exists()

    def get_documento_list(self, obj):
        return [
            {'documento_id': d.documento_id, 'documento_idno': d.documento_idno, 'titulo': d.titulo}
            for d in obj.documentos.all()
        ]

    def get_calidades(self, obj):
        return [c.calidad for c in obj.calidades.all()]

    def get_documented_span(self, obj):
        earliest = getattr(obj, 'earliest_doc_date', None)
        latest = getattr(obj, 'latest_doc_date', None)
        if earliest and latest and earliest != latest:
            return (latest.year - earliest.year) or 1
        return None


class PersonaNoEsclavizadaListSerializer(PersonaListSerializer):
    """PersonaNoEsclavizada data for list views"""
    has_relaciones = serializers.SerializerMethodField()
    has_lugares = serializers.SerializerMethodField()
    documento_list = serializers.SerializerMethodField()
    ocupaciones = serializers.SerializerMethodField()
    calidades = serializers.SerializerMethodField()

    class Meta(PersonaListSerializer.Meta):
        model = PersonaNoEsclavizada
        fields = PersonaListSerializer.Meta.fields + [
            'has_relaciones', 'has_lugares', 'documento_list',
            'ocupaciones', 'calidades',
        ]

    def get_has_relaciones(self, obj):
        return obj.relaciones.exists()

    def get_has_lugares(self, obj):
        return obj.p_x_l_pere.exists()

    def get_documento_list(self, obj):
        return [
            {'documento_id': d.documento_id, 'documento_idno': d.documento_idno, 'titulo': d.titulo}
            for d in obj.documentos.all()
        ]

    def get_ocupaciones(self, obj):
        return [a.actividad for a in obj.ocupaciones.all()]

    def get_calidades(self, obj):
        return [c.calidad for c in obj.calidades.all()]


class LugarListSerializer(serializers.ModelSerializer):
    """Lugar data for list views"""
    persona_count = serializers.SerializerMethodField()
    persona_lugar_rel = serializers.SerializerMethodField()

    class Meta:
        model = Lugar
        fields = ['lugar_id', 'nombre_lugar', 'otros_nombres', 'tipo', 'lat', 'lon',
                  'persona_count', 'persona_lugar_rel']

    def get_persona_count(self, obj):
        return Persona.objects.filter(
            Q(p_x_l_pere__lugar=obj) |
            Q(lugar_nacimiento=obj) |
            Q(lugar_defuncion=obj) |
            Q(personaesclavizada__procedencia=obj)
        ).distinct().count()

    def get_persona_lugar_rel(self, obj):
        from dbgestor.models import PersonaLugarRel
        return list(
            PersonaLugarRel.objects.filter(lugar=obj)
            .values_list('persona_x_lugares', flat=True)
        )


class CorporacionListSerializer(serializers.ModelSerializer):
    """Corporacion data for list views"""
    tipo_institucion = serializers.CharField(source='get_tipo_institucion', read_only=True)
    lugar_corporacion = LugarReferenceSerializer(read_only=True)

    class Meta:
        model = Corporacion
        fields = ['corporacion_id', 'nombre_institucion', 'tipo_institucion', 'lugar_corporacion']


# Detail Serializers - Full entity data with references instead of nested objects
class ArchivoDetailSerializer(serializers.ModelSerializer):
    """Full Archivo details"""
    nombre_abreviado = serializers.CharField(read_only=True)
    documento_count = serializers.SerializerMethodField()

    class Meta:
        model = Archivo
        fields = ['archivo_id', 'nombre', 'nombre_abreviado', 'archivo_idno', 
                  'documento_count', 'created_at', 'updated_at']

    def get_documento_count(self, obj):
        return obj.documento_set.count()


class DocumentoDetailSerializer(serializers.ModelSerializer):
    """Full Documento details"""
    archivo = ArchivoReferenceSerializer(read_only=True)
    tipo_documento = serializers.StringRelatedField()
    lugar_de_produccion = LugarReferenceSerializer(read_only=True)
    persona_count = serializers.SerializerMethodField()

    class Meta:
        model = Documento
        fields = ['documento_id', 'documento_idno', 'archivo', 'fondo', 'subfondo', 'serie', 'subserie',
                  'tipo_udc', 'unidad_documental_compuesta', 'tipo_documento', 'sigla_documento',
                  'titulo', 'descripcion', 'deteriorado', 'fecha_inicial', 'fecha_inicial_raw', 'fecha_final',
                  'fecha_final_raw', 'lugar_de_produccion', 'folio_inicial', 'folio_final', 'notas', 
                  'persona_count', 'created_at', 'updated_at']

    def get_persona_count(self, obj):
        return obj.persona_set.count()


# Nested serializers for detail views (map + network visualizations)
class LugarNestedSerializer(serializers.ModelSerializer):
    """Lugar with coordinates for map rendering"""
    class Meta:
        model = Lugar
        fields = ['lugar_id', 'nombre_lugar', 'tipo', 'lat', 'lon']


class PersonaLugarRelNestedSerializer(serializers.ModelSerializer):
    """PersonaLugarRel with nested Lugar for the detail map"""
    lugar = LugarNestedSerializer(read_only=True)
    situacion_lugar = serializers.StringRelatedField()

    class Meta:
        model = PersonaLugarRel
        fields = ['persona_x_lugares', 'lugar', 'situacion_lugar', 'ordinal',
                  'fecha_inicial_lugar']


class PersonaRelacionesNestedSerializer(serializers.ModelSerializer):
    """PersonaRelaciones with nested persona refs for network graph"""
    personas = PersonaReferenceSerializer(many=True, read_only=True)

    class Meta:
        model = PersonaRelaciones
        fields = ['persona_relacion_id', 'personas', 'naturaleza_relacion',
                  'descripcion_relacion']


class DocumentoNestedSerializer(serializers.ModelSerializer):
    """Documento with archivo ref for the detail documents section"""
    archivo = ArchivoReferenceSerializer(read_only=True)
    tipo_documento = serializers.StringRelatedField()

    class Meta:
        model = Documento
        fields = ['documento_id', 'documento_idno', 'archivo', 'titulo',
                  'tipo_documento', 'fecha_inicial', 'fecha_final']


class PersonaDetailSerializer(serializers.ModelSerializer):
    """Base Persona detail serializer"""
    sexo = serializers.CharField(source='get_sexo_display', read_only=True)
    documentos = DocumentoNestedSerializer(many=True, read_only=True)
    relaciones = PersonaRelacionesNestedSerializer(many=True, read_only=True)
    lugares = PersonaLugarRelNestedSerializer(source='p_x_l_pere', many=True, read_only=True)
    lugar_nacimiento = LugarNestedSerializer(read_only=True)
    lugar_defuncion = LugarNestedSerializer(read_only=True)

    class Meta:
        model = Persona
        fields = ['persona_id', 'persona_idno', 'nombre_normalizado', 'nombres', 'apellidos',
                  'sexo', 'polymorphic_ctype', 'documentos', 'relaciones', 'lugares',
                  'lugar_nacimiento', 'lugar_defuncion',
                  'created_at', 'updated_at']


class PersonaEsclavizadaDetailSerializer(PersonaDetailSerializer):
    """Full PersonaEsclavizada details with nested relations for visualization"""
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
        lugar = getattr(obj, 'procedencia', None)
        if lugar:
            return LugarNestedSerializer(lugar).data
        return None

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


class LugarDetailSerializer(serializers.ModelSerializer):
    """Full Lugar details"""
    procedencia_count = serializers.SerializerMethodField()

    class Meta:
        model = Lugar
        fields = ['lugar_id', 'nombre_lugar', 'otros_nombres', 'tipo', 'lat', 'lon',
                  'procedencia_count']

    def get_procedencia_count(self, obj):
        return obj.procedencia_persona_esclavizada.count()


class LugarPersonasRelSerializer(serializers.ModelSerializer):
    """PersonaLugarRel records for a lugar's personas view."""
    personas = PersonaReferenceSerializer(many=True, read_only=True)
    documento = DocumentoReferenceSerializer(read_only=True)
    situacion_lugar = serializers.StringRelatedField()

    class Meta:
        model = PersonaLugarRel
        fields = ['persona_x_lugares', 'personas', 'documento', 'situacion_lugar',
                  'ordinal', 'fecha_inicial_lugar_raw', 'fecha_final_lugar_raw']


class CorporacionDetailSerializer(serializers.ModelSerializer):
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
class PersonaRelacionesDetailSerializer(serializers.ModelSerializer):
    """PersonaRelaciones with references"""
    documento = DocumentoReferenceSerializer(read_only=True)
    persona_ids = serializers.SerializerMethodField()

    class Meta:
        model = PersonaRelaciones
        fields = ['persona_relacion_id', 'documento', 'persona_ids', 'naturaleza_relacion', 'descripcion_relacion']

    def get_persona_ids(self, obj):
        return list(obj.personas.values_list('persona_id', flat=True))


class PersonaLugarRelDetailSerializer(serializers.ModelSerializer):
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


class PersonaRolEventoDetailSerializer(serializers.ModelSerializer):
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
class TravelTrajectorySerializer(serializers.ModelSerializer):
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

    def _collect_fk_places(self, obj):
        """Collect direct FK place fields (nacimiento, procedencia, defuncion)."""
        fk_places = []
        seen_ids = set()

        nac = getattr(obj, 'lugar_nacimiento', None)
        if nac:
            fk_places.append(('Nacimiento', nac, -2))
            seen_ids.add(nac.lugar_id)

        if isinstance(obj, PersonaEsclavizada):
            proc = getattr(obj, 'procedencia', None)
            if proc and proc.lugar_id not in seen_ids:
                fk_places.append(('Procedencia', proc, -1))

        defn = getattr(obj, 'lugar_defuncion', None)
        if defn:
            fk_places.append(('Defunción', defn, None))  # ordinal set after rel points

        return fk_places

    def get_trajectory_summary(self, obj):
        """Summary statistics for the trajectory"""
        lugares = obj.p_x_l_pere.all().order_by('ordinal')
        fk_places = self._collect_fk_places(obj)
        fk_count = len(fk_places)
        fk_lugar_ids = {lugar.lugar_id for _, lugar, _ in fk_places}

        rel_count = lugares.count()
        rel_lugar_ids = set(lugares.values_list('lugar_id', flat=True).distinct())

        first_rel = lugares.first()
        last_rel = lugares.last()

        earliest = first_rel.fecha_inicial_lugar or (first_rel.documento.fecha_inicial if first_rel and first_rel.documento else None) if first_rel else None
        latest = last_rel.fecha_inicial_lugar or (last_rel.documento.fecha_inicial if last_rel and last_rel.documento else None) if last_rel else None

        return {
            'total_locations': rel_count + fk_count,
            'date_range': {
                'earliest': earliest,
                'latest': latest,
            },
            'unique_places': len(rel_lugar_ids | fk_lugar_ids),
        }

    def get_trajectory_points(self, obj):
        """Lightweight trajectory points for map rendering, including FK places."""
        lugares = obj.p_x_l_pere.select_related('lugar', 'documento').all().order_by('ordinal')
        fk_places = self._collect_fk_places(obj)

        # Determine ordinal bounds
        ordinals = [rel.ordinal for rel in lugares]
        min_ordinal = min(ordinals) if ordinals else 1
        max_ordinal = max(ordinals) if ordinals else 0

        points = []

        # Prepend FK places (nacimiento, procedencia)
        for situacion, lugar, base_ordinal in fk_places:
            if situacion == 'Defunción':
                ordinal = max_ordinal + 1
            else:
                ordinal = base_ordinal if base_ordinal is not None else min_ordinal - 1
            points.append({
                'lugar_id': lugar.lugar_id,
                'nombre_lugar': lugar.nombre_lugar,
                'tipo_lugar': lugar.tipo,
                'lat': float(lugar.lat) if lugar.lat else None,
                'lon': float(lugar.lon) if lugar.lon else None,
                'fecha': None,
                'ordinal': ordinal,
                'situacion': situacion,
                'documento_id': None,
                'documento_titulo': None,
            })

        # Add persona_x_lugares points
        for rel in lugares:
            points.append({
                'lugar_id': rel.lugar.lugar_id,
                'nombre_lugar': rel.lugar.nombre_lugar,
                'tipo_lugar': rel.lugar.tipo,
                'lat': float(rel.lugar.lat) if rel.lugar.lat else None,
                'lon': float(rel.lugar.lon) if rel.lugar.lon else None,
                'fecha': rel.fecha_inicial_lugar or (rel.documento.fecha_inicial if rel.documento else None),
                'ordinal': rel.ordinal,
                'situacion': str(rel.situacion_lugar) if rel.situacion_lugar else None,
                'documento_id': rel.documento.documento_id if rel.documento else None,
                'documento_titulo': rel.documento.titulo if rel.documento else None,
            })

        points.sort(key=lambda p: p['ordinal'])
        return points


# Simple utility serializers
class ActividadesSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Actividades
        fields = ['actividad_id', 'actividad']


class LogMessageSerializer(serializers.ModelSerializer):
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


# ── Write Serializers ─────────────────────────────────────────────────────────
# Used for POST / PUT / PATCH.  Validation ported from dbgestor/forms.py.

def _parse_flexible_date(value):
    """
    Accept DD-MM-YYYY, MM-YYYY, or YYYY.  Returns a date object.
    Raises serializers.ValidationError on failure.
    """
    if not isinstance(value, str):
        return value
    value = value.strip().replace('/', '-')
    for fmt in ('%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    parts = value.split('-')
    if len(parts) == 1 and len(parts[0]) == 4:
        try:
            return datetime.strptime(value, '%Y').date()
        except ValueError:
            pass
    if len(parts) == 2:
        try:
            return datetime.strptime(value, '%m-%Y').date()
        except ValueError:
            pass
    raise serializers.ValidationError(
        f"Formato de fecha incorrecto: '{value}'. Use DD-MM-AAAA, MM-AAAA, o AAAA."
    )


def _validate_folios(folio_inicial, folio_final):
    if not folio_inicial or folio_inicial == 'None':
        return
    if not folio_final:
        return
    ini_nums = re.findall(r'^[1-9]\d*', str(folio_inicial))
    fin_nums = re.findall(r'^[1-9]\d*', str(folio_final))
    if not ini_nums or not fin_nums:
        return
    ini, fin = int(ini_nums[0]), int(fin_nums[0])
    if fin < ini:
        raise serializers.ValidationError(
            f"El folio final ({folio_final}) no puede ser menor que el inicial ({folio_inicial})."
        )
    if fin == ini:
        ori_ini = re.findall(r'\w$', str(folio_inicial))
        ori_fin = re.findall(r'\w$', str(folio_final))
        if ori_ini and ori_fin and ori_ini != ori_fin:
            if ori_ini[0].lower() != 'r':
                raise serializers.ValidationError(
                    f"La orientación de los folios ({folio_inicial} - {folio_final}) es incorrecta."
                )


class ArchivoWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Archivo
        fields = ['nombre', 'nombre_abreviado', 'ubicacion_archivo']
        extra_kwargs = {'nombre_abreviado': {'required': False}}


class LugarWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lugar
        fields = ['nombre_lugar', 'otros_nombres', 'es_parte_de', 'lat', 'lon', 'tipo']
        extra_kwargs = {
            'otros_nombres': {'required': False},
            'es_parte_de': {'required': False},
            'lat': {'required': False},
            'lon': {'required': False},
        }

    def validate(self, data):
        lat, lon = data.get('lat'), data.get('lon')
        if (lat is None) != (lon is None):
            raise serializers.ValidationError(
                'Latitud y longitud deben proporcionarse juntas.'
            )
        return data


class DocumentoWriteSerializer(serializers.ModelSerializer):
    fecha_inicial = serializers.CharField()
    fecha_final = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Documento
        exclude = ['documento_idno', 'search_vector', 'is_published',
                   'fecha_inicial_raw', 'fecha_final_raw']

    def validate(self, data):
        raw_ini = data.get('fecha_inicial', '').strip()
        raw_fin = (data.get('fecha_final') or '').strip()

        data['fecha_inicial_raw'] = raw_ini
        data['fecha_final_raw'] = raw_fin if raw_fin else raw_ini

        parsed_ini = _parse_flexible_date(raw_ini)
        parsed_fin = _parse_flexible_date(raw_fin) if raw_fin else parsed_ini

        if parsed_ini > parsed_fin:
            raise serializers.ValidationError(
                'La fecha final no puede ser anterior a la fecha inicial.'
            )
        data['fecha_inicial'] = parsed_ini
        data['fecha_final'] = parsed_fin

        folio_ini = data.get('folio_inicial')
        folio_fin = data.get('folio_final')
        if data.get('deteriorado') and not folio_ini:
            data['folio_inicial'] = '[ilegible]'
        else:
            _validate_folios(folio_ini, folio_fin)

        return data

    def create(self, validated_data):
        validated_data.setdefault('fecha_final_raw', validated_data.get('fecha_inicial_raw', ''))
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.setdefault('fecha_final_raw', validated_data.get('fecha_inicial_raw', ''))
        return super().update(instance, validated_data)


class PersonaEsclavizadaWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonaEsclavizada
        exclude = ['persona_idno', 'search_vector']


class PersonaNoEsclavizadaWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonaNoEsclavizada
        exclude = ['persona_idno', 'search_vector']


class CorporacionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Corporacion
        exclude = ['corporacion_idno', 'search_vector']


class PersonaLugarRelWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonaLugarRel
        fields = '__all__'

    def validate_ordinal(self, value):
        if value == 0:
            raise serializers.ValidationError('0 no es un valor permitido para el ordinal.')
        return value


class PersonaRelacionesWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonaRelaciones
        fields = '__all__'


class PersonaRolEventoWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonaRolEvento
        fields = '__all__'


class InstitucionRolEventoWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstitucionRolEvento
        fields = '__all__'


# ── Vocabulary Write Serializers (update_or_create with title-casing) ─────────

class _VocabUpsertMixin:
    """Mixin that implements update_or_create with title-casing for the main text field."""
    vocab_field: str = ''

    def create(self, validated_data):
        validated_data[self.vocab_field] = validated_data[self.vocab_field].title()
        obj, _ = self.Meta.model.objects.update_or_create(
            **{self.vocab_field: validated_data[self.vocab_field]},
            defaults=validated_data,
        )
        return obj

    def update(self, instance, validated_data):
        validated_data[self.vocab_field] = validated_data[self.vocab_field].title()
        return super().update(instance, validated_data)


class TipoDocumentalWriteSerializer(_VocabUpsertMixin, serializers.ModelSerializer):
    vocab_field = 'tipo_documental'

    class Meta:
        model = TipoDocumental
        fields = ['tipo_documental']


class CalidadesWriteSerializer(_VocabUpsertMixin, serializers.ModelSerializer):
    vocab_field = 'calidad'

    class Meta:
        model = Calidades
        fields = ['calidad']


class HispanizacionesWriteSerializer(_VocabUpsertMixin, serializers.ModelSerializer):
    vocab_field = 'hispanizacion'

    class Meta:
        model = Hispanizaciones
        fields = ['hispanizacion']


class EtnonimosWriteSerializer(_VocabUpsertMixin, serializers.ModelSerializer):
    vocab_field = 'etonimo'

    class Meta:
        model = Etonimos
        fields = ['etonimo']


class EstadoCivilWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstadoCivil
        fields = ['estado_civil']


class ActividadesWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Actividades
        fields = ['actividad']


class SituacionLugarWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SituacionLugar
        fields = ['situacion', 'descripcion']
        extra_kwargs = {'descripcion': {'required': False}}


class RolEventoWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolEvento
        fields = ['rol_evento', 'descripcion']
        extra_kwargs = {'descripcion': {'required': False}}


class TiposInstitucionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TiposInstitucion
        fields = ['tipo', 'descripcion']
        extra_kwargs = {'descripcion': {'required': False}}