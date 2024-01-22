from django.db import models
from simple_history.models import HistoricalRecords

import logging

logger = logging.getLogger("dbgestor")
# Create your models here.


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
        ('fuerte', 'Fuerte')
    )

UDC = (
        ('exp', 'Expediente'),
        ('caj', 'Caja'),
        ('vol', 'Volumen'),
        ('leg', 'Legajo')
    )

SITUACION_LUGAR = (
        ('vecino', 'Vecino'), 
        ('residente', 'Residente'), 
        ('estante', 'Estante')
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

PERSONAS_TIPOS = (
        ('pere', 'Persona Esclavizada'),
        ('peri', 'Persona involucrada')
    )

RELACIONES = (
        ('fam', 'Familiar'), 
        ('aso', 'Asociativa'), 
        ('tmp', 'Temporal')
    )
 
###############
# Lugares
###############

class Lugar(models.Model):
    lugar_id = models.AutoField(primary_key=True)
    nombre_lugar = models.CharField(max_length=255)
    es_parte_de = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lon = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    tipo = models.CharField(max_length=50, choices=PLACE_TYPE_CHOICES)
    
    history = HistoricalRecords()
    
    def __str__(self) -> str:
        return f"{self.nombre_lugar} ({self.tipo})"


class HistoricalName(models.Model):
    
    lugar = models.ForeignKey(Lugar, on_delete=models.CASCADE, related_name='historical_names')
    nombre = models.CharField(max_length=255)
    fecha_inicial = models.DateField()
    fecha_final = models.DateField(null=True, blank=True)
    tipo = models.CharField(max_length=50, choices=PLACE_TYPE_CHOICES)
    narrativa = models.TextField(null=True, blank=True)
    
    history = HistoricalRecords()
    
    def __str__(self):
        return f"{self.nombre} ({self.fecha_inicial} - {self.fecha_final or 'Present'})"
    
####################
# Documento
####################

class Archivo(models.Model):
    
    archivo_id = models.AutoField(primary_key=True)
    
    nombre = models.CharField(max_length=255)
    nombre_abreviado = models.CharField(max_length=50)
    ubicacion_archivo = models.ForeignKey(Lugar, on_delete=models.SET_NULL, null=True, blank=True, related_name='archivos_lugares')
    
    history = HistoricalRecords()
    
    def __str__(self) -> str:
        return f'[{self.nombre_abreviado}] {self.nombre}'

class Documento(models.Model):
    
    documento_id = models.AutoField(primary_key=True)
    
    archivo = models.ForeignKey(Archivo, on_delete=models.CASCADE)
    fondo = models.CharField(max_length=200)
    subfondo = models.CharField(max_length=200, null=True, blank=True)
    serie = models.CharField(max_length=200, null=True, blank=True)
    subserie = models.CharField(max_length=200, null=True, blank=True)
    tipo_udc = models.CharField(max_length=50, choices=UDC, default='exp')
    unidad_documental_compuesta = models.CharField(max_length=200)
    
    tipo_documento = models.CharField(max_length=100) # este campo necesita una lista de tipos documentales
    sigla_documento = models.CharField(max_length=100)
    
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    
    folio_inicial = models.CharField(max_length=50)
    folio_final = models.CharField(max_length=50, null=True, blank=True)
    
    history = HistoricalRecords()

    def __str__(self) -> str:
        return f'{self.archivo}, {self.sigla_documento}: {self.titulo}'


#####################
# Autoridad Personas
#####################

class Calidades(models.Model):
    """
    This table has the only purpose to serve as basic vocabulary for Calidades in Autoridades
    and to be used in forms with Select2 autocomplete
    """
    
    calidad_id = models.AutoField(primary_key=True)
    calidad = models.CharField(max_length=150)
    descripcion = models.TextField(null=True, blank=True)
    
    def __str__(self) -> str:
        return f'{self.calidad}'
    
class HistorialActividadesPersona(models.Model):
    
    historial_actividades_persona = models.AutoField(primary_key=True)
    tipo_actividad = models.CharField(max_length=200)
    descripcion_actividad = models.JSONField(null=True, blank=True)
    fecha_inicial_actividad = models.DateField(null=True, blank=True)
    fecha_final_actividad = models.DateField(null=True, blank=True)
    lugares_actividad = models.ManyToManyField(Lugar)
    
    history = HistoricalRecords()
    
    def __str__(self) -> str:
        return f'({self.fecha_inicial_actividad} - {self.fecha_final_actividad}) {self.tipo_actividad}, {self.persona}'
    

class LugaresPersona(models.Model):
    
    persona_lugar_id = models.AutoField(primary_key=True)

    lugar = models.ForeignKey(Lugar, on_delete=models.CASCADE, related_name='historial_lugares_personas')
    fecha_inicial = models.DateField(null=True, blank=True)
    fecha_final = models.DateField(null=True, blank=True)
    situacion_lugar = models.CharField(max_length=150, null=True, blank=True, choices=SITUACION_LUGAR)
    
    def __str__(self) -> str:
        return f'{self.lugar}'

    
class Hispanizaciones(models.Model):
    """
    This table has the only purpose to serve as basic vocabulary for Hispanizaciones for Persona Esclavizada
    """
    
    hispanizacion_id = models.AutoField(primary_key=True)
    hispanizacion = models.CharField(max_length=150)
    descripcion = models.TextField(null=True, blank=True)
    
    def __str__(self) -> str:
        return f'{self.hispanizacion}'


class Etonimos(models.Model):
    """
    This table has the only purpose to serve as basic vocabulary for Etonimos for Persona Esclavizada
    """
    
    etonimo_id = models.AutoField(primary_key=True)
    etonimo = models.CharField(max_length=150)
    descripcion = models.TextField(null=True, blank=True)
    
    def __str__(self) -> str:
        return f'{self.etonimo}'

class PersonaEsclavizadaExp(models.Model):
    """
    This table expands Persona to specifics features regarding a Persona Esclavizada
    """
    
    persona_esclavizada_exp_id = models.AutoField(primary_key=True)
    sexo = models.CharField(max_length=50, choices=SEXOS)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    altura = models.CharField(max_length=150, null=True, blank=True)
    cabello = models.CharField(max_length=150, null=True, blank=True)
    ojos = models.CharField(max_length=150, null=True, blank=True)
    hispanizacion = models.ManyToManyField(Hispanizaciones)
    etonimos = models.ManyToManyField(Etonimos)
    
    marcas_corporales = models.TextField(null=True, blank=True)
    conducta = models.TextField(null=True, blank=True)
    
    ocupacion = models.ForeignKey(HistorialActividadesPersona, null=True, blank=True, on_delete=models.CASCADE, related_name='ocupacion_pere')
    transito_origen = models.ForeignKey(LugaresPersona, null=True, blank=True, on_delete=models.CASCADE, related_name='tran_ori_pere')
    transito_destino = models.ForeignKey(LugaresPersona, null=True, blank=True, on_delete=models.CASCADE, related_name='tran_des_pere')
    

class PersonaInvolucradaExp(models.Model):
    persona_involucrada_caracteristicas = models.AutoField(primary_key=True)
    sexo = models.CharField(max_length=50, choices=SEXOS)
    
    honorifico = models.CharField(max_length=100, choices=HONORIFICOS, default='nan')
    
    ocupacion = models.ForeignKey(HistorialActividadesPersona, null=True, blank=True, on_delete=models.CASCADE, related_name='ocupacion_pero')
    rol_evento = models.CharField(max_length=100, null=True, blank=True, default="nan")
    lugar_situacion = models.ForeignKey(LugaresPersona, null=True, blank=True, on_delete=models.CASCADE, related_name='lugar_situa_peri')

class Persona(models.Model):
    
    autoridad_id = models.AutoField(primary_key=True)
    
    tipo_persona = models.CharField(max_length=50, choices=PERSONAS_TIPOS, default='pere')
    nombres = models.CharField(max_length=150, help_text="Nombres sin honoríficos", default="Anónimo")
    apellidos = models.CharField(max_length=150, blank=True, null=True)
    nombre_normalizado = models.CharField(max_length=300, null=True, blank=True)
    
    caracteristicas_persona_esclavizada = models.ForeignKey(PersonaEsclavizadaExp, on_delete=models.SET_NULL, null=True, blank=True, related_name='pere_caracteristicas')
    caracteristicas_persona_involucrada = models.ForeignKey(PersonaInvolucradaExp, on_delete=models.SET_NULL, null=True, blank=True, related_name='peri_caracteristicas')
    
    calidades = models.ManyToManyField(Calidades)
    
    # Dates of existence
    
    fecha_nacimiento = models.DateField(null=True, blank=True)
    lugar_nacimiento = models.ForeignKey(Lugar, on_delete=models.SET_NULL, null=True, blank=True, related_name='lugar_nac')
    
    fecha_defuncion = models.DateField(null=True, blank=True)
    lugar_defuncion = models.ForeignKey(Lugar, on_delete=models.SET_NULL, null=True, blank=True, related_name='lugar_def')
    
    history = HistoricalRecords()
    
    def save(self, *args, **kwargs):
        
        if not self.nombre_normalizado and self.nombres or self.apellidos:
            self.nombre_normalizado = f'{self.nombres} {self.apellidos}'.strip()
            
        super().save(*args, **kwargs)
    
    def __str__(self) -> str:
        dates = " - ".join(filter(None, [str(self.fecha_nacimiento) if self.fecha_nacimiento else None, 
                                            str(self.fecha_defuncion) if self.fecha_defuncion else None]))
        return f'{self.nombre_normalizado} ({dates})' if dates else f'{self.nombre_normalizado}'
        


class PersonaRelaciones(models.Model):
    
    persona_relacion_id = models.AutoField(primary_key=True)
    
    persona1 = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name='persona')
    persona2 = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name='persona_relacion')
    naturaleza_relacion = models.CharField(max_length=50, choices=RELACIONES)
    descripcion_relacion = models.CharField(max_length=250)
    fecha_inicial_relacion = models.DateField(null=True, blank=True)
    fecha_final_relacion = models.DateField(null=True, blank=True)
    
    history = HistoricalRecords()
    
    def __str__(self) -> str:
        return f'{self.persona1} > {self.descripcion_relacion} > {self.persona2}'


#############
# Eventos
#############

class Evento(models.Model):
    evento_id = models.AutoField(primary_key=True)
    tipo_evento = models.CharField(max_length=150)
    fecha_evento = models.DateField()
    lugar_evento = models.ForeignKey(Lugar, on_delete=models.SET_NULL, null=True, blank=True)
    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name='documentos_eventos')
    descripcion = models.TextField(null=True, blank=True, help_text="Descripción del evento")
    
    valor_evento_sp = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    forma_de_pago = models.CharField(max_length=100, null=True, blank=True)
    valor_total = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    moneda = models.CharField(max_length=100, null=True, blank=True)
    
    personas_esclavizadas = models.ManyToManyField(Persona, related_name='eventos_pere')
    personas_involucradas = models.ManyToManyField(Persona, related_name='eventos_peri')
    
    def __str__(self) -> str:
        return f'{self.tipo_evento} ({self.fecha_evento})'


