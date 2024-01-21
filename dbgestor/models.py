from django.db import models
import json

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

class Evento(models.Model):
    
    evento_id = models.AutoField(primary_key=True)
    

class Documento(models.Model):
    
    documento_id = models.AutoField(primary_key=True)
    

class Persona(models.Model):
    
    persona_id = models.AutoField(primary_key=True)
    

class Lugar(models.Model):
    lugar_id = models.AutoField(primary_key=True)
    nombre_lugar = models.CharField(max_length=255)
    es_parte_de = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lon = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    def __str__(self) -> str:
        return f"{self.nombre_lugar} ({self.parent.nombre_lugar if self.es_parte_de else 'No parent'})"

class HistoricalName(models.Model):
    lugar = models.ForeignKey(Lugar, on_delete=models.CASCADE, related_name="historical_names")
    name = models.CharField(max_length=255)
    fecha_inicial = models.DateField()
    fecha_final = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.fecha_inicial} - {self.fecha_final or 'Present'})"

class LugarTipo(models.Model):
    tipo = models.CharField(max_length=50, choices=PLACE_TYPE_CHOICES)
    lugar = models.ForeignKey(Lugar, on_delete=models.CASCADE, related_name="tipos")
    
    def __str__(self):
        return f"{self.tipo} for {self.lugar.nombre_lugar}"


class TaxonomiaEventos(models.Model):
    """
    This table serves as controlled vocabulary for Eventos
    """
    taxonomia_id = models.AutoField(primary_key=True)


class RecordsHistory(models.Model):
    """
    This table keeps the CRUD record for each entity
    """    
    record_id = models.AutoField(primary_key=True)


