from typing import Any
from django import forms
from datetime import datetime
from dal import autocomplete
import re

from .models import Lugar, PlaceHistorical


import logging

logger = logging.getLogger("dbgestor")

class LugarForm(forms.ModelForm):
    
    class Meta:
        model = Lugar
        fields = '__all__'
    
    es_parte_de = forms.ModelChoiceField(required=False,
            queryset=Lugar.objects.all(),
            widget=autocomplete.ModelSelect2(url='lugar-autocomplete'),
            help_text="Seleccione o añada un lugar."
        )
    lat = forms.DecimalField(max_digits=9, decimal_places=6, required=False)
    lon = forms.DecimalField(max_digits=9, decimal_places=6, required=False)
    
    def clean(self):
        cleaned_data = super().clean()
        lat = cleaned_data.get('lat')
        lon = cleaned_data.get('lon')
        
        if (lat is not None and lon is None) or (lat is None and lon is not None):
            raise forms.ValidationError("Both latitude and longitude are required together.")

        return cleaned_data
    
    def save(self, commit=True):
        lugar = super().save(commit=False)
        logger.debug("LugarForm save method called.")
        
        if 'nombre_lugar' in self.changed_data or 'tipo' in self.changed_data:
            # Assume lugar instance already exists and we are updating it
            PlaceHistorical.objects.create(
                lugar=lugar,
                nombre_original=lugar.nombre_lugar,
                fecha_inicial=datetime(1500,1,1),
                tipo_original=lugar.tipo
            )

        if commit:
            lugar.save()

        return lugar
        
    
class LugarHistoria(forms.ModelForm):
    
    class Meta:
        model = PlaceHistorical
        fields = '__all__'
    
    lugar = forms.ModelChoiceField(
        queryset=Lugar.objects.all(),
        widget=autocomplete.ModelSelect2(url='lugar-autocomplete')
    )
    
    fecha_inicial = forms.DateField(required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'date-input'}, format='%Y-%m-%d'),
        input_formats=['%Y-%m-%d']
    )
    fecha_final = forms.DateField(required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'date-input'}, format='%Y-%m-%d'),
        input_formats=['%Y-%m-%d']
    )
    
    def save(self) -> Any:
        logger.debug("LugarHistoria save method called.")
    
        lugar_tipo = super().save(commit=False)
        lugar_tipo.save()