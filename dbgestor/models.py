import re
from django.db import models
from simple_history.models import HistoricalRecords
from polymorphic.models import PolymorphicModel
from datetime import timezone

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
        ('m', 'Mujer')
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

class TipoDocumental(models.Model):
    
    tipo_documental = models.CharField(max_length=70, unique=True)
    descripcion = models.TextField(null=True, blank=True)
    
    def __str__(self) -> str:
        return f'{self.tipo_documental}'

class RolEvento(models.Model):
    
    rol_evento = models.CharField(max_length=70, unique=True)
    descripcion = models.TextField(null=True, blank=True)
    
    def __str__(self) -> str:
        return f'{self.rol_evento}'

class TipoLugar(models.Model):
    
    tipo_lugar = models.CharField(max_length=70, unique=True)
    descripcion = models.TextField(null=True, blank=True)
    
    def __str__(self) -> str:
        return f'{self.tipo_lugar}'

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
    
    def __str__(self) -> str:
        return f"{self.nombre_lugar} ({self.tipo})"


    
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
    
    #tipo_documento = models.CharField(max_length=100, choices=TIPOS_DOCUMENTALES, default='ccv')
    tipo_documento =  models.ForeignKey(TipoDocumental, on_delete=models.SET_NULL, default=1, null=True, related_name='tipo_documento')
    sigla_documento = models.CharField(max_length=100, null=True, blank=True)
    
    titulo = models.CharField(max_length=200, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    
    deteriorado = models.BooleanField(default=False)
    
    fecha_inicial = models.DateField(null=True, blank=True)
    fecha_inicial_aproximada = models.BooleanField(null=True, blank=True)
    fecha_final = models.DateField(null=True, blank=True)
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

    def __str__(self) -> str:
        if self.sigla_documento:
            return f'{self.archivo.nombre_abreviado}, {self.sigla_documento}: {self.titulo[:50]}'
        else:
            return f'{self.archivo.nombre_abreviado}: {self.titulo[:50]}'


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
    

class Actividades(models.Model):
    
    actividad_id = models.AutoField(primary_key=True)
    actividad = models.CharField(max_length=150, unique=True)
    descripcion = models.TextField(null=True, blank=True)
    
    def __str__(self) -> str:
        return f'{self.actividad}'

class Hispanizaciones(models.Model):
    """
    This table has the only purpose to serve as basic vocabulary for Hispanizaciones for Persona Esclavizada
    """
    
    hispanizacion_id = models.AutoField(primary_key=True)
    hispanizacion = models.CharField(max_length=150, unique=True)
    descripcion = models.TextField(null=True, blank=True)
    
    def __str__(self) -> str:
        return f'{self.hispanizacion}'


class Etonimos(models.Model):
    """
    This table has the only purpose to serve as basic vocabulary for Etonimos for Persona Esclavizada
    """
    
    etonimo_id = models.AutoField(primary_key=True)
    etonimo = models.CharField(max_length=150, unique=True)
    descripcion = models.TextField(null=True, blank=True)
    
    def __str__(self) -> str:
        return f'{self.etonimo}'

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
    fecha_nacimiento_factual = models.BooleanField(null=True, blank=True)
    lugar_nacimiento = models.ForeignKey(Lugar, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(class)s_lugar_nac')
    
    fecha_defuncion = models.DateField(null=True, blank=True)
    fecha_defuncion_factual = models.BooleanField(null=True, blank=True)
    lugar_defuncion = models.ForeignKey(Lugar, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(class)s_lugar_def')
    
    sexo = models.CharField(max_length=50, choices=SEXOS)

    ocupacion = models.ForeignKey(Actividades, null=True, blank=True, on_delete=models.CASCADE, related_name='%(class)s_ocupacion_per')
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

    def __str__(self) -> str:
        dates = " - ".join(filter(None, [str(self.fecha_nacimiento) if self.fecha_nacimiento else None, 
                                            str(self.fecha_defuncion) if self.fecha_defuncion else None]))
        return f'{self.nombre_normalizado} ({self.persona_idno})'
    

class PersonaEsclavizada(Persona):
    """
    This table expands Persona to specifics features regarding a Persona Esclavizada
    """
    edad = models.IntegerField(null=True, blank=True)
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

class PersonaNoEsclavizada(Persona):
    
    entidad_asociada = models.CharField(max_length=100, blank=True)
    honorifico = models.CharField(max_length=100, choices=HONORIFICOS, default='nan')


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
    fecha_inicial_lugar_factual = models.BooleanField(null=True, blank=True)
    fecha_final_lugar = models.DateField(null=True, blank=True)
    fecha_final_lugar_factual = models.BooleanField(null=True, blank=True)
    
    notas = models.TextField(max_length=500, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    history = HistoricalRecords()

    def __str__(self) -> str:
        return ', '.join([persona.nombre_normalizado for persona in self.personas.all()]) + f" - ({self.ordinal}){self.lugar}"

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
    fecha_inicial_relacion_factual = models.BooleanField(null=True, blank=True)
    fecha_final_relacion = models.DateField(null=True, blank=True)
    fecha_final_relacion_factual = models.BooleanField(null=True, blank=True)
    
    notas = models.TextField(max_length=500, null=True, blank=True)
    
    history = HistoricalRecords()
    
    def __str__(self) -> str:
        return ', '.join([persona.nombre_normalizado for persona in self.personas.all()]) + f" - {self.get_naturaleza_relacion_display()}"


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
    

class TiposInstitucion(models.Model):
    
    tipo_id = models.AutoField(primary_key=True)
    tipo = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(null=True, blank=True)
    
    def __str__(self) -> str:
        return f'{self.tipo}'
    

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
    
    
    
    
    
    
