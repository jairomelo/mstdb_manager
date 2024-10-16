import re
from django.db import models
from simple_history.models import HistoricalRecords
from polymorphic.models import PolymorphicModel
from datetime import timezone
from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

import logging

logger = logging.getLogger("dbgestor")
# Create your models here.

UDC = (
        ('exp', 'Expediente'),
        ('caj', 'Caja'),
        ('vol', 'Volumen'),
        ('lib', 'Libro'),
        ('leg', 'Legajo')
    )

SEXOS = (
        ('v', 'Varón'), 
        ('m', 'Mujer'),
        ('i', 'Desconocido')
    )

HONORIFICOS = (
        ('nan', 'N/A'), 
        ('don', 'Don'), 
        ('dna', 'Doña'), 
        ('doc', 'Doctor'), 
        ('fra', 'Fray')
    )

PLACE_TYPE_CHOICES = (
        ('ciudad', 'Ciudad'),
        ('pueblo', 'Pueblo'),
        ('estado', 'Estado'),
        ('gobernacion', 'Gobernación'),
        ('pais', 'País'),
        ('provincia', 'Provincia'),
        ('villa', 'Villa'),
        ('real', 'Real de Minas'),
        ('parroquia', 'Parroquia'),
        ('fuerte', 'Fuerte'),
        ('puerto', 'Puerto'),
        ('isla', 'Isla'),
        ('region', 'Región'),
        ('diocesis', 'Diócesis')
    )


###############
# Vocabularies
# Not so strict as controlled vocabularies, but a little more controled than a simple charfield.
###############


class SituacionLugar(models.Model):
    situacion_id = models.AutoField(primary_key=True)
    situacion = models.CharField(max_length=150, unique=True)
    descripcion = models.TextField(null=True, blank=True)
    
    def __str__(self) -> str:
        return f'{self.situacion}'

@registry.register_document
class SituacionLugarDocument(Document):
    class Index:
        name = 'situacionlugar'  # Name of the Elasticsearch index

    class Django:
        model = SituacionLugar
        fields = ['situacion']
        
class TipoDocumental(models.Model):
    
    tipo_documental = models.CharField(max_length=70, unique=True)
    descripcion = models.TextField(null=True, blank=True)
    
  
    def __str__(self) -> str:
        return f'{self.tipo_documental}'

@registry.register_document
class TipoDocumentalDocument(Document):
    class Index:
        name = 'tipodocumental'

    class Django:
        model = TipoDocumental
        fields = ['tipo_documental', 'descripcion']
class RolEvento(models.Model):
    
    rol_evento = models.CharField(max_length=70, unique=True)
    descripcion = models.TextField(null=True, blank=True)
       
    def __str__(self) -> str:
        return f'{self.rol_evento}'

@registry.register_document
class RolEventoDocument(Document):
    class Index:
        name = 'rolevento'

    class Django:
        model = RolEvento
        fields = ['rol_evento', 'descripcion']
        
class TipoLugar(models.Model):
    
    tipo_lugar = models.CharField(max_length=70, unique=True)
    descripcion = models.TextField(null=True, blank=True)
    
    def __str__(self) -> str:
        return f'{self.tipo_lugar}'

@registry.register_document
class TipoLugarDocument(Document):
    class Index:
        name = 'tipolugar'

    class Django:
        model = TipoLugar
        fields = ['tipo_lugar', 'descripcion']

###############
# Lugares
###############

class Lugar(models.Model):
    
    lugar_id = models.AutoField(primary_key=True)
    nombre_lugar = models.CharField(max_length=255)
    otros_nombres = models.TextField(null=True, blank=True)
    es_parte_de = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lon = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    tipo = models.CharField(max_length=50, choices=PLACE_TYPE_CHOICES)
    
    history = HistoricalRecords()
    
    def type_to_string(self):
        if self.tipo == 'ciudad':
            return 'Ciudad'
        elif self.tipo == 'pueblo':
            return 'Pueblo'
        elif self.tipo == 'estado':
            return 'Estado'
        elif self.tipo == 'gobernacion':
            return 'Gobernación'
        elif self.tipo == 'pais':
            return 'País'
        elif self.tipo == 'provincia':
            return 'Provincia'
        elif self.tipo == 'villa':
            return 'Villa'
        elif self.tipo == 'real':
            return 'Real de Minas'
        elif self.tipo == 'parroquia':
            return 'Parroquia'
        elif self.tipo == 'fuerte':
            return 'Fuerte'
        elif self.tipo == 'puerto':
            return 'Puerto'
        elif self.tipo == 'isla':
            return 'Isla'
        elif self.tipo == 'region':
            return 'Región'
        elif self.tipo == 'diocesis':
            return 'Diócesis'
        else:
            return 'Desconocido'
    
    def __str__(self) -> str:
        return f"{self.nombre_lugar} ({self.type_to_string()})"

@registry.register_document
class LugarDocument(Document):
    nombre_lugar = fields.TextField(attr='nombre_lugar')
    otros_nombres = fields.TextField(attr='otros_nombres')
    tipo = fields.TextField(attr='tipo')
    es_parte_de = fields.ObjectField(attr='es_parte_de',
                                     properties={
                                        'nombre_lugar': fields.TextField(attr='nombre_lugar'),
                                        'tipo': fields.TextField(attr='tipo')
                                     })
    
    class Index:
        name = 'lugar'

    class Django:
        model = Lugar
        


####################
# Documento
####################

class Archivo(models.Model):
    
    archivo_id = models.AutoField(primary_key=True)
    
    archivo_idno = models.CharField(max_length=50, null=True, blank=True)
    
    nombre = models.CharField(max_length=255, unique=True)
    nombre_abreviado = models.CharField(max_length=50, null=True, blank=True)
    ubicacion_archivo = models.ForeignKey(Lugar, on_delete=models.SET_NULL, null=True, blank=True, related_name='archivos_lugares')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    history = HistoricalRecords()
    
    class Meta:
        ordering = ['-updated_at']
    
    def create_acronym(self, text):
        
        connectors = ["de", "del", "la", "las", "los", "a", "y"]
        
        words = re.findall(r'\b\w+\b', text)
        acronym = ""
        for word in words:
            if word not in connectors:
                acronym += word[0].upper()
                
        return acronym
    
    def save(self, *args, **kwargs):
        
        if not self.nombre_abreviado:
            siglas = self.create_acronym(self.nombre)
            self.nombre_abreviado = siglas
        
        if not self.pk:
            super(Archivo, self).save(*args, **kwargs)
            
        self.archivo_idno = f"mx-sv-doc-{str(self.archivo_id).zfill(6)}"

        super(Archivo, self).save(*args, **kwargs)
    
    def __str__(self) -> str:
        return f'[{self.nombre_abreviado}] {self.nombre}'

@registry.register_document
class ArchivoDocument(Document):
    ubicacion_archivo = fields.ObjectField(attr='ubicacion_archivo',
                                     properties={
                                        'nombre_lugar': fields.TextField(attr='nombre_lugar'),
                                        'tipo': fields.TextField(attr='tipo')
                                     })
    
    class Index:
        name = 'archivo'

    class Django:
        model = Archivo
        fields = ['nombre', 'nombre_abreviado', 'archivo_idno']

class Documento(models.Model):
    
    documento_id = models.AutoField(primary_key=True)
    
    documento_idno = models.CharField(max_length=50, null=True, blank=True)
    
    archivo = models.ForeignKey(Archivo, on_delete=models.CASCADE)
    fondo = models.CharField(max_length=200)
    subfondo = models.CharField(max_length=200, null=True, blank=True)
    serie = models.CharField(max_length=200, null=True, blank=True)
    subserie = models.CharField(max_length=200, null=True, blank=True)
    tipo_udc = models.CharField(max_length=50, choices=UDC, default='lib')
    unidad_documental_compuesta = models.CharField(max_length=200)
    
    tipo_documento =  models.ForeignKey(TipoDocumental, on_delete=models.SET_NULL, default=1, null=True, related_name='tipo_documento')
    sigla_documento = models.CharField(max_length=100, null=True, blank=True)
    
    titulo = models.CharField(max_length=300)
    descripcion = models.TextField(blank=True, null=True)
    
    deteriorado = models.BooleanField(default=False)
    
    fecha_inicial = models.DateField(null=True, blank=True)
    fecha_inicial_raw = models.CharField(max_length=10, blank=True, null=True)
    fecha_inicial_aproximada = models.BooleanField(null=True, blank=True)
    fecha_final = models.DateField(null=True, blank=True)
    fecha_final_raw = models.CharField(max_length=10, blank=True, null=True)
    fecha_final_aproximada = models.BooleanField(null=True, blank=True)
    
    lugar_de_produccion = models.ForeignKey(Lugar, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(class)s_lugar_doc')
    
    folio_inicial = models.CharField(max_length=50)
    folio_final = models.CharField(max_length=50, null=True, blank=True)
    
    evento_valor_sp = models.CharField(max_length=50, null=True, blank=True)
    evento_forma_de_pago = models.CharField(max_length=100, null=True, blank=True)
    evento_total = models.CharField(max_length=100, null=True, blank=True)
    
    notas = models.TextField(max_length=500, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    history = HistoricalRecords()

    class Meta:
        ordering = ['-updated_at']
        
    def save(self, *args, **kwargs):
        self.documento_idno = f"mx-sv-doc-{str(self.documento_id).zfill(6)}"

        super(Documento, self).save(*args, **kwargs)

    def type_to_string(self):
        if self.tipo_udc == 'exp':
            return 'Expediente'
        elif self.tipo_udc == 'caj':
            return 'Caja'
        elif self.tipo_udc == 'vol':
            return 'Volumen'
        elif self.tipo_udc == 'lib':
            return 'Libro'
        elif self.tipo_udc == 'leg':
            return 'Legajo'
        else:
            return 'Desconocido'

    def __str__(self) -> str:
        if self.sigla_documento:
            return f'{self.archivo.nombre_abreviado}, {self.sigla_documento}: {self.titulo[:50]}'
        else:
            return f'{self.archivo.nombre_abreviado}: {self.titulo[:50]}'

@registry.register_document
class DocumentoDocument(Document):
    archivo = fields.ObjectField(attr='archivo',
                                 properties={
                                    'nombre': fields.TextField(attr='nombre'),
                                    'nombre_abreviado': fields.TextField(attr='nombre_abreviado')
                                 })
    tipo_documento = fields.ObjectField(attr='tipo_documento',
                                        properties={
                                            'tipo_documental': fields.TextField(attr='tipo_documental')
                                        })
    lugar_de_produccion = fields.ObjectField(attr='lugar_de_produccion',
                                             properties={
                                                'nombre_lugar': fields.TextField(attr='nombre_lugar'),
                                                'tipo': fields.TextField(attr='tipo')
                                             })
    
    class Index:
        name = 'documento'

    class Django:
        model = Documento
        fields = ['documento_idno', 'fondo', 'subfondo', 'serie', 'subserie', 'tipo_udc', 
                  'unidad_documental_compuesta', 'sigla_documento', 'titulo', 'descripcion', 
                  'deteriorado', 'fecha_inicial', 'fecha_final', 'folio_inicial', 'folio_final', 
                  'evento_valor_sp', 'evento_forma_de_pago', 'evento_total', 'notas']


#####################
# Autoridad Personas
#####################

class Calidades(models.Model):
    """
    This table has the only purpose to serve as basic vocabulary for Calidades in Autoridades
    and to be used in forms with Select2 autocomplete
    """
    
    calidad_id = models.AutoField(primary_key=True)
    calidad = models.CharField(max_length=150, unique=True)
    descripcion = models.TextField(null=True, blank=True)
    
    def __str__(self) -> str:
        return f'{self.calidad}'
    

@registry.register_document
class CalidadesDocument(Document):
    class Index:
        name = 'calidades'

    class Django:
        model = Calidades
        fields = ['calidad']
class Actividades(models.Model):
    
    actividad_id = models.AutoField(primary_key=True)
    actividad = models.CharField(max_length=150, unique=True)
    descripcion = models.TextField(null=True, blank=True)
    
    def __str__(self) -> str:
        return f'{self.actividad}'

@registry.register_document
class ActividadesDocument(Document):
    class Index:
        name = 'actividades'

    class Django:
        model = Actividades
        fields = ['actividad']
class Hispanizaciones(models.Model):
    """
    This table has the only purpose to serve as basic vocabulary for Hispanizaciones for Persona Esclavizada
    """
    
    hispanizacion_id = models.AutoField(primary_key=True)
    hispanizacion = models.CharField(max_length=150, unique=True)
    descripcion = models.TextField(null=True, blank=True)
    
    def __str__(self) -> str:
        return f'{self.hispanizacion}'

@registry.register_document
class HispanizacionesDocument(Document):
    class Index:
        name = 'hispanizaciones'

    class Django:
        model = Hispanizaciones
        fields = ['hispanizacion']

class Etonimos(models.Model):
    """
    This table has the only purpose to serve as basic vocabulary for Etonimos for Persona Esclavizada
    """
    
    etonimo_id = models.AutoField(primary_key=True)
    etonimo = models.CharField(max_length=150, unique=True)
    descripcion = models.TextField(null=True, blank=True)
    
    def __str__(self) -> str:
        return f'{self.etonimo}'

@registry.register_document
class EtonimosDocument(Document):
    class Index:
        name = 'etonimos'

    class Django:
        model = Etonimos
        fields = ['etonimo']

class EstadoCivil(models.Model):
    """
    Estado civil de las personas
    """
    
    estado_civil = models.CharField(max_length=150, unique=True)
    descripcion = models.TextField(null=True, blank=True)
    
    def __str__(self) -> str:
        return f'{self.estado_civil}'

@registry.register_document
class EstadoCivilDocument(Document):
    class Index:
        name = 'estadocivil'

    class Django:
        model = EstadoCivil
        fields = ['estado_civil']

##########
# Handling Person Information:
# ----------------------------
# This model acts as polymorphic model for `PersonaEsclavizada` and `PersonaNoEsclavizada`,
# encapsulating common information applicable to all persona entities. It provides the flexibility
# to add or modify custom fields specific to enslaved or non-enslaved personas without altering
# the shared attributes defined here. 
##########

class Persona(PolymorphicModel):
    
    persona_id = models.AutoField(primary_key=True)
    
    persona_idno = models.CharField(max_length=50, null=True, blank=True)
    
    documentos = models.ManyToManyField(Documento)
    
    nombres = models.CharField(max_length=150, help_text="Nombres sin honoríficos", default="Anónimo")
    apellidos = models.CharField(max_length=150, blank=True, null=True)
    nombre_normalizado = models.CharField(max_length=300, null=True, blank=True)
    
    entidades_asociadas = models.ManyToManyField('Corporacion', blank=True)
    
    calidades = models.ManyToManyField(Calidades)
    
    # Dates of existence
    
    fecha_nacimiento = models.DateField(null=True, blank=True)
    fecha_nacimiento_raw = models.CharField(max_length=10, blank=True, null=True)
    fecha_nacimiento_factual = models.BooleanField(null=True, blank=True)
    lugar_nacimiento = models.ForeignKey(Lugar, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(class)s_lugar_nac')
    
    fecha_defuncion = models.DateField(null=True, blank=True)
    fecha_defuncion_raw = models.CharField(max_length=10, blank=True, null=True)
    fecha_defuncion_factual = models.BooleanField(null=True, blank=True)
    lugar_defuncion = models.ForeignKey(Lugar, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(class)s_lugar_def')
    
    sexo = models.CharField(max_length=50, choices=SEXOS)
    
    estado_civil = models.ManyToManyField(EstadoCivil, blank=True)

    ocupaciones = models.ManyToManyField(Actividades, related_name='%(class)s_ocupaciones_per', blank=True)
    ocupacion_categoria = models.CharField(max_length=150, null=True, blank=True)
    
    notas = models.TextField(max_length=500, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    history = HistoricalRecords(inherit=True)
    
    def capitalize_name(self, name):
        
        name_connectors = ["de", "del", "la", "y", "e"]
        
        nombre_capitalizado = ""
        
        name = name.split()
        
        for palabra in name:
            palabra = palabra.lower()
            if palabra not in name_connectors:
                palabra = palabra.title()
                nombre_capitalizado += f" {palabra} "
            else:
                nombre_capitalizado += f" {palabra} "
                
        return nombre_capitalizado
    
    def persona_type(self):
        if isinstance(self, PersonaEsclavizada):
            return 'esclavizada'
        elif isinstance(self, PersonaNoEsclavizada):
            return 'noesclavizada'
        return None
    
    def save(self, *args, **kwargs):
        
        if self.nombres:
            self.nombres = self.capitalize_name(self.nombres)
        
        if self.apellidos:
            self.apellidos = self.capitalize_name(self.apellidos)
        elif not self.apellidos:
            self.apellidos = ""
        
        if not self.nombre_normalizado:
            nombre_normalizado = f"{self.nombres} {self.apellidos}"
            self.nombre_normalizado = self.capitalize_name(nombre_normalizado)
        
        if not self.pk:
            super(Persona, self).save(*args, **kwargs)
            
        self.persona_idno = f"mx-sv-per-{str(self.persona_id).zfill(6)}"

        super(Persona, self).save(*args, **kwargs)

    def type_to_string(self):
        if self.sexo == 'v':
            return 'Varón'
        elif self.sexo == 'm':
            return 'Mujer'
        else:
            return 'Desconocido'

    def __str__(self) -> str:
        dates = " - ".join(filter(None, [str(self.fecha_nacimiento) if self.fecha_nacimiento else None, 
                                            str(self.fecha_defuncion) if self.fecha_defuncion else None]))
        return f'{self.nombre_normalizado} ({self.persona_idno})'
    

@registry.register_document
class PersonaDocument(Document):
    calidades = fields.NestedField(properties={
        'calidad': fields.TextField()
    })
    lugar_nacimiento = fields.ObjectField(attr='lugar_nacimiento',
                                          properties={
                                             'nombre_lugar': fields.TextField(attr='nombre_lugar'),
                                             'tipo': fields.TextField(attr='tipo')
                                          })
    lugar_defuncion = fields.ObjectField(attr='lugar_defuncion',
                                         properties={
                                            'nombre_lugar': fields.TextField(attr='nombre_lugar'),
                                            'tipo': fields.TextField(attr='tipo')
                                         })
    estado_civil = fields.NestedField(properties={
        'estado_civil': fields.TextField()
    })
    ocupaciones = fields.NestedField(properties={
        'actividad': fields.TextField()
    })
    
    class Index:
        name = 'persona'

    class Django:
        model = Persona
        fields = ['persona_idno', 'nombres', 'apellidos', 'nombre_normalizado', 'sexo', 
                  'fecha_nacimiento', 'fecha_defuncion', 'ocupacion_categoria', 'notas']
        
        
class PersonaEsclavizada(Persona):
    """
    This table expands Persona to specifics features regarding a Persona Esclavizada
    """
    UNIDADTEMP = (
        ('d', 'días'),
        ('m', 'meses'),
        ('a', 'años')
    )
    
    edad = models.IntegerField(null=True, blank=True)
    unidad_temporal_edad = models.CharField(choices=UNIDADTEMP, max_length=20, null=True, blank=True)
    altura = models.CharField(max_length=150, null=True, blank=True)
    cabello = models.CharField(max_length=150, null=True, blank=True)
    ojos = models.CharField(max_length=150, null=True, blank=True)
    hispanizacion = models.ManyToManyField(Hispanizaciones)
    etnonimos = models.ManyToManyField(Etonimos)
    
    procedencia = models.ForeignKey(Lugar, on_delete=models.SET_NULL, null=True, blank=True, related_name='procedencia_persona_esclavizada')
    procedencia_adicional = models.CharField(max_length=200, null=True, blank=True)
    
    marcas_corporales = models.TextField(null=True, blank=True)
    conducta = models.TextField(null=True, blank=True)
    salud = models.TextField(null=True, blank=True)
    
    def type_to_string(self):
        if self.unidad_temporal_edad == 'd':
            return 'Días'
        elif self.unidad_temporal_edad == 'm':
            return 'Meses'
        elif self.unidad_temporal_edad == 'a':
            return 'Años'
        else:
            return 'Desconocido'
     
    def __str__(self) -> str:
        return f'{self.nombre_normalizado} ({self.persona_idno})'

@registry.register_document
class PersonaEsclavizadaDocument(PersonaDocument):
    persona_idno = fields.KeywordField(attr='persona_idno')
    nombre_normalizado = fields.TextField(attr='nombre_normalizado')
    sexo = fields.TextField(attr='sexo')
    edad = fields.IntegerField(attr='edad')
    unidad_temporal_edad = fields.TextField(attr='unidad_temporal_edad')
    altura = fields.TextField(attr='altura')
    cabello = fields.TextField(attr='cabello')
    ojos = fields.TextField(attr='ojos')

    hispanizacion = fields.NestedField(properties={
        'hispanizacion': fields.TextField()
    })

    etnonimos = fields.NestedField(properties={
        'etnonimo': fields.TextField()
    })

    procedencia = fields.ObjectField(attr='procedencia', properties={
        'nombre_lugar': fields.TextField(attr='nombre_lugar'),
        'tipo': fields.TextField(attr='tipo')
    })

    procedencia_adicional = fields.TextField(attr='procedencia_adicional')
    marcas_corporales = fields.TextField(attr='marcas_corporales')
    conducta = fields.TextField(attr='conducta')
    salud = fields.TextField(attr='salud')

    class Index:
        name = 'personas_esclavizadas'

    class Django:
        model = PersonaEsclavizada
        
class PersonaNoEsclavizada(Persona):
    
    entidad_asociada = models.CharField(max_length=100, blank=True)
    honorifico = models.CharField(max_length=100, choices=HONORIFICOS, default='nan')
    
    def type_to_string(self):
        if self.honorifico == 'nan':
            return 'N/A'
        elif self.honorifico == 'don':
            return 'Don'
        elif self.honorifico == 'dna':
            return 'Doña'
        elif self.honorifico == 'doc':
            return 'Doctor'
        elif self.honorifico == 'dra':
            return 'Dra.'
        elif self.honorifico == 'sra':
            return 'Sra.'
        elif self.honorifico == 'sr':
            return 'Sr.'
        elif self.honorifico == 'sn':
            return 'Sn.'
        else:
            return 'Desconocido'
    
    def __str__(self) -> str:
        return f'{self.nombre_normalizado} ({self.persona_idno})'

@registry.register_document
class PersonaNoEsclavizadaDocument(PersonaDocument):
    class Index:
        name = 'personanoesclavizada'

    class Django:
        model = PersonaNoEsclavizada
        fields = ['entidad_asociada', 'honorifico']

class PersonaLugarRel(models.Model):
    
    persona_x_lugares = models.AutoField(primary_key=True)
    
    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name='p_x_l_documento')
    
    personas = models.ManyToManyField(
        Persona, 
        related_name='p_x_l_pere'
    )
    
    lugar = models.ForeignKey(Lugar, on_delete=models.CASCADE, related_name='p_x_l_lugar')
    
    situacion_lugar = models.ForeignKey(SituacionLugar, blank=True, null=True, on_delete=models.SET_NULL, related_name='situacion_lugar')
    
    ordinal = models.SmallIntegerField(default=0) 

    fecha_inicial_lugar = models.DateField(null=True, blank=True)
    fecha_inicial_lugar_raw = models.CharField(max_length=10, blank=True, null=True)
    fecha_inicial_lugar_factual = models.BooleanField(null=True, blank=True)
    fecha_final_lugar = models.DateField(null=True, blank=True)
    fecha_final_lugar_raw = models.CharField(max_length=10, blank=True, null=True)
    fecha_final_lugar_factual = models.BooleanField(null=True, blank=True)
    
    notas = models.TextField(max_length=500, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    history = HistoricalRecords()

    def __str__(self) -> str:
        return ', '.join([persona.nombre_normalizado for persona in self.personas.all()]) + f" - ({self.ordinal}){self.lugar}"

@registry.register_document
class PersonaLugarRelDocument(Document):
    documento = fields.ObjectField(attr='documento',
                                   properties={
                                      'titulo': fields.TextField(attr='titulo'),
                                      'documento_idno': fields.TextField(attr='documento_idno')
                                   })
    personas = fields.NestedField(properties={
        'nombre_normalizado': fields.TextField(),
        'persona_idno': fields.TextField()
    })
    lugar = fields.ObjectField(attr='lugar',
                               properties={
                                  'nombre_lugar': fields.TextField(attr='nombre_lugar'),
                                  'tipo': fields.TextField(attr='tipo')
                               })
    situacion_lugar = fields.ObjectField(attr='situacion_lugar',
                                         properties={
                                            'situacion': fields.TextField(attr='situacion')
                                         })
    
    class Index:
        name = 'personalugarrel'

    class Django:
        model = PersonaLugarRel
        fields = ['ordinal', 'fecha_inicial_lugar', 'fecha_final_lugar', 'notas']

class PersonaRelaciones(models.Model):
    
    RELACIONES = (
        ('fam', 'Familiar'), 
        ('aso', 'Asociativa'), 
        ('tmp', 'Temporal')
    )
    
    persona_relacion_id = models.AutoField(primary_key=True)
    
    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name='p_x_p_documento', default=1)
    
    personas = models.ManyToManyField(
        Persona, 
        related_name='relaciones'
    )
    naturaleza_relacion = models.CharField(max_length=50, choices=RELACIONES)
    descripcion_relacion = models.CharField(max_length=250, null=True, blank=True)
    
    fecha_inicial_relacion = models.DateField(null=True, blank=True)
    fecha_inicial_relacion_raw = models.CharField(max_length=10, blank=True, null=True)
    fecha_inicial_relacion_factual = models.BooleanField(null=True, blank=True)
    fecha_final_relacion = models.DateField(null=True, blank=True)
    fecha_final_relacion_raw = models.CharField(max_length=10, blank=True, null=True)
    fecha_final_relacion_factual = models.BooleanField(null=True, blank=True)
    
    notas = models.TextField(max_length=500, null=True, blank=True)
    
    history = HistoricalRecords()
    
    def type_to_string(self):
        if self.naturaleza_relacion == 'fam':
            return 'Familiar'
        elif self.naturaleza_relacion == 'aso':
            return 'Asociativa'
        elif self.naturaleza_relacion == 'tmp':
            return 'Temporal'
        else:
            return 'Desconocido'
    
    def __str__(self) -> str:
        return ', '.join([persona.nombre_normalizado for persona in self.personas.all()]) + f" - {self.get_naturaleza_relacion_display()}"

@registry.register_document
class PersonaRelacionesDocument(Document):
    documento = fields.ObjectField(attr='documento',
                                   properties={
                                      'titulo': fields.TextField(attr='titulo'),
                                      'documento_idno': fields.TextField(attr='documento_idno')
                                   })
    personas = fields.NestedField(properties={
        'nombre_normalizado': fields.TextField(),
        'persona_idno': fields.TextField()
    })
    
    class Index:
        name = 'personalrelaciones'

    class Django:
        model = PersonaRelaciones
        fields = ['naturaleza_relacion', 'descripcion_relacion', 'fecha_inicial_relacion', 
                  'fecha_final_relacion', 'notas']


class PersonaRolEvento(models.Model):
    
    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name='rol_evento_documento', blank=True)
    
    personas = models.ManyToManyField(
        Persona, 
        related_name='p_roles_evento'
    )
    
    rol_evento = models.ForeignKey(RolEvento, on_delete=models.CASCADE,
                                   related_name="rol_evento_personas")
      
    def __str__(self) -> str:
        return ', '.join([persona.nombre_normalizado for persona in self.personas.all()])
    

@registry.register_document
class PersonaRolEventoDocument(Document):
    documento = fields.ObjectField(attr='documento',
                                   properties={
                                      'titulo': fields.TextField(attr='titulo'),
                                      'documento_idno': fields.TextField(attr='documento_idno')
                                   })
    personas = fields.NestedField(properties={
        'nombre_normalizado': fields.TextField(),
        'persona_idno': fields.TextField()
    })
    rol_evento = fields.ObjectField(attr='rol_evento',
                                    properties={
                                       'rol_evento': fields.TextField(attr='rol_evento')
                                    })
    
    class Index:
        name = 'personalrolevento'

    class Django:
        model = PersonaRolEvento
        
class TiposInstitucion(models.Model):
    
    tipo_id = models.AutoField(primary_key=True)
    tipo = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(null=True, blank=True)
    
    def __str__(self) -> str:
        return f'{self.tipo}'
    

@registry.register_document
class TiposInstitucionDocument(Document):
    class Index:
        name = 'tiposinstitucion'

    class Django:
        model = TiposInstitucion
        fields = ['tipo']
class Corporacion(PolymorphicModel):
    
    corporacion_id = models.AutoField(primary_key=True)
    
    corporacion_idno = models.CharField(max_length=50, null=True, blank=True)
    
    documentos = models.ManyToManyField(Documento)
    
    tipo_institucion = models.ForeignKey(TiposInstitucion, on_delete=models.CASCADE)
    
    nombre_institucion = models.CharField(max_length=100, unique=True)
    
    nombres_alternativos = models.TextField(blank=True, null=True)
    
    personas_asociadas = models.ManyToManyField(Persona, blank=True) #! optional
    
    notas = models.TextField(max_length=500, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    history = HistoricalRecords()
    
    def save(self, *args, **kwargs):
        
        if not self.pk:
            super(Corporacion, self).save(*args, **kwargs)
            
        self.corporacion_idno = f"mx-sv-cor-{str(self.corporacion_id).zfill(6)}"

        super(Corporacion, self).save(*args, **kwargs)
    
    def __str__(self) -> str:
        return f"{self.nombre_institucion}"
    
    
@registry.register_document
class CorporacionDocument(Document):
    tipo_institucion = fields.ObjectField(attr='tipo_institucion',
                                          properties={
                                             'tipo': fields.TextField(attr='tipo')
                                          })
    personas_asociadas = fields.NestedField(properties={
        'nombre_normalizado': fields.TextField(),
        'persona_idno': fields.TextField()
    })
    
    class Index:
        name = 'corporacion'

    class Django:
        model = Corporacion
        fields = ['corporacion_idno', 'nombre_institucion', 'nombres_alternativos', 'notas']
class InstitucionRolEvento(models.Model):
    
    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name='institucion_rol_evento_documento', blank=True)
    
    corporaciones = models.ManyToManyField(
        Corporacion, 
        related_name='p_roles_evento'
    )
    
    rol_evento = models.ForeignKey(RolEvento, on_delete=models.CASCADE,
                                   related_name="rol_evento_institucion")
    
    def __str__(self) -> str:
        return ', '.join([corporaciones.nombre_institucion for corporaciones in self.corporaciones.all()])
    
    
@registry.register_document
class InstitucionRolEventoDocument(Document):
    documento = fields.ObjectField(attr='documento',
                                   properties={
                                      'titulo': fields.TextField(attr='titulo'),
                                      'documento_idno': fields.TextField(attr='documento_idno')
                                   })
    corporaciones = fields.NestedField(properties={
        'nombre_institucion': fields.TextField(),
        'corporacion_idno': fields.TextField()
    })
    rol_evento = fields.ObjectField(attr='rol_evento',
                                    properties={
                                       'rol_evento': fields.TextField(attr='rol_evento')
                                    })
    
    class Index:
        name = 'institucionrolevento'

    class Django:
        model = InstitucionRolEvento
        