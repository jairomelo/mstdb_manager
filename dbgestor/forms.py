from typing import Any
from django import forms
from django.utils.translation import gettext_lazy as _
from datetime import datetime
from dal import autocomplete
import re

from .models import (Lugar, PersonaEsclavizada, 
                     PersonaNoEsclavizada, Persona, Documento, Archivo,
                     Calidades, Hispanizaciones, Etonimos, Actividades,
                     PersonaLugarRel, PersonaRelaciones, TipoLugar,
                     SituacionLugar, TipoDocumental, RolEvento)

from .widgets import (PersonaEsclavizadaAutocomplete, PersonaNoEsclavizadaAutocomplete, 
                      LugarEventoAutocomplete, DocumentoAutocomplete, ArchivoAutocomplete, CalidadesAutocomplete)

import logging

logger = logging.getLogger("dbgestor")


class CustomValidators:
    def validate_date(self, date_text):
        if not isinstance(date_text, str):
            return date_text
        date_text = date_text.strip()
        if len(date_text) > 10:
            raise forms.ValidationError(f"El formato de la fecha {date_text} es incorrecto. Use DD-MM-AAAA, MM-AAAA, o AAAA.")
        
        date_text = date_text.replace("/", "-")
        
        try:
            parsed_date = datetime.strptime(date_text, '%d-%m-%Y')
            return parsed_date.date()
        except ValueError:
            parts = date_text.split('-')
            if len(parts) == 1 and len(parts[0]) == 4:
                return datetime.strptime(date_text, '%Y').date()
            elif len(parts) == 2:
                return datetime.strptime(date_text, '%m-%Y').date()
            else:
                raise forms.ValidationError(f"El formato de la fecha {date_text} es incorrecto. Use DD-MM-AAAA, MM-AAAA, o AAAA.")


    def validate_date_range(self, date_inicial, date_final):
        
        if date_inicial > date_final:
            raise forms.ValidationError(f"La fecha final {date_final} no puede estar en el pasado de la fecha inicial {date_inicial}")

    def validate_folios(self, folio_inicial, folio_final):
        
        folio_inicial = str(folio_inicial)
        folio_final = str(folio_final) if folio_final else folio_inicial
        
        fininum = re.findall(r'^[1-9]\d*', folio_inicial)
        ffinnum = re.findall(r'^[1-9]\d*', folio_final)
        
        # Extract the first element from the list and convert to integer
        fininum = int(fininum[0])
        ffinnum = int(ffinnum[0])

        if ffinnum < fininum:
            raise forms.ValidationError(f"El valor de {folio_final} no puede ser menor que {folio_inicial}")
        elif fininum == ffinnum:
            folium_orientation_ini = re.findall(r"\w$", folio_inicial)
            folium_orientation_fin = re.findall(r"\w$", folio_final)
            if folium_orientation_ini != folium_orientation_fin:
                if folium_orientation_ini[0].lower() != 'r':
                    raise forms.ValidationError(f"La orientación de los folios ({folio_inicial} - {folio_final}) es incorrecta")


class CustomBuilders:
    def nacimiento_x_edad(self, edad, fecha_referencia):
        
        if edad and edad != "":
            anio = fecha_referencia.year
            fecha_nacimiento = anio - int(edad)
            return CustomValidators().validate_date(str(fecha_nacimiento))
        else:
            return None

    def edad_x_nacimiento(self, fecha_nacimiento, fecha_referencia):
        
        if fecha_nacimiento and fecha_nacimiento != "":
            anio_nac = fecha_nacimiento.year
            anio_ref = fecha_referencia.year
            
            edad = max(anio_ref, anio_nac) - min(anio_ref, anio_nac)
            return edad
        else:
            return None


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
        
        if commit:
            lugar.save()
            

        return lugar
    
    def __init__(self, *args, **kwargs):
        super(LugarForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
    


class ArchivoForm(forms.ModelForm):
    class Meta:
        model = Archivo
        fields = '__all__'
        widgets = {
            'ubicacion_archivo': LugarEventoAutocomplete()
        }
    
    def __init__(self, *args, **kwargs):
        super(ArchivoForm, self).__init__(*args, **kwargs)
        
        self.fields['nombre'].widget.attrs['class'] = 'form-control'
        self.fields['nombre_abreviado'].widget.attrs['class'] = 'form-control'



class DocumentoForm(forms.ModelForm):
    class Meta:
        model = Documento
        fields = '__all__'
        widgets = {
            'archivo': ArchivoAutocomplete()
        }
    
    unidad_documental_compuesta = forms.CharField(widget=forms.TextInput(attrs={'placeholder': _('Número de la unidad')}))
    
    titulo = forms.CharField(label= _('Título/resumen del documento'))
    
    folio_inicial = forms.CharField(widget=forms.TextInput(attrs={'placeholder': _('incluir número y \'r\' o \'v\'')}))
    folio_final = forms.CharField(widget=forms.TextInput(attrs={'placeholder': _('folio final opcional')}), required=False)
    
    fecha_inicial = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'date-input', 'placeholder': _('DD-MM-AAAA, MM-AAAA, o AAAA.')}),
        required=True 
    )
    
    fecha_final = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'date-input', 'placeholder': _('DD-MM-AAAA, MM-AAAA, o AAAA.')}),
        required=False
    )
    
    tipo_documento = forms.ModelChoiceField(
        queryset=TipoDocumental.objects.all(),
        required=False,
        widget=autocomplete.ModelSelect2(url='tiposdocumentales-autocomplete'),
        label='Tipo documental'
    )
    
    def clean_fecha_inicial(self):
        
        fecha_inicial = self.cleaned_data.get('fecha_inicial')
        logger.debug(f"Cleaning Documento/fecha_inicial {fecha_inicial}")
        
        fecha_inicial_valid = CustomValidators().validate_date(fecha_inicial)
        logger.debug(f"Fecha inicial cleaned {fecha_inicial_valid}")
        
        return fecha_inicial_valid
    
    def clean_fecha_final(self):
        
        fecha_final = self.cleaned_data.get('fecha_final')
        logger.debug(f"Cleaning Documento/fecha_final \"{fecha_final}\"")
        
        if not fecha_final or fecha_final == "":
            fecha_final = self.cleaned_data.get('fecha_inicial', '')
            return fecha_final
        
        fecha_final_valid = CustomValidators().validate_date(fecha_final)
        logger.debug(f"Fecha final cleaned {fecha_final_valid}")
        
        return fecha_final_valid
    
    def clean_folio_inicial(self):
        folio_inicial = self.cleaned_data.get('folio_inicial')
        if not folio_inicial or folio_inicial == "":
            raise forms.ValidationError(f"El valor del folio inicial no puede estar vacío.")
            
        pat = re.compile(r'^\d+[rv]$')
        
        if not re.fullmatch(pat, folio_inicial):
            raise forms.ValidationError(f"El formato de {folio_inicial} no es correcto.\nEj: 25r o 25v")
        
        return folio_inicial

    def clean_folio_final(self):
        folio_final = self.cleaned_data.get('folio_final')

        # If folio_final is empty, use folio_inicial as folio_final
        if not folio_final:
            folio_inicial = self.cleaned_data.get('folio_inicial', '')
            return folio_inicial

        # Validate the format of folio_final
        pat = re.compile(r'^\d+[rv]$')
        if not re.fullmatch(pat, folio_final):
            raise forms.ValidationError(f"El formato de {folio_final} no es correcto.\nEj: 25r o 25v")
        
        return folio_final
    
    def clean(self):
        cleaned_data = super().clean()
        folio_inicial = cleaned_data.get('folio_inicial')
        folio_final = cleaned_data.get('folio_final')

        try:
            CustomValidators().validate_folios(folio_inicial, folio_final)
            logger.debug(f"folios {folio_inicial} y {folio_final} validados")
        except forms.ValidationError as e:
            # Add the error to the form's error list
            self.add_error(None, e)
            
        fecha_inicial = cleaned_data.get('fecha_inicial')
        fecha_final = cleaned_data.get('fecha_final')
        logger.debug(f"validando si {fecha_final} existe")
        try:
            logger.debug(f"validando {fecha_inicial}")
            fecha_inicial = CustomValidators().validate_date(fecha_inicial)
            if fecha_final:
                logger.debug(f"validando {fecha_final}")
                fecha_final = CustomValidators().validate_date(fecha_final)
                CustomValidators().validate_date_range(fecha_inicial, fecha_final)
        except forms.ValidationError as e:
            logger.warning(e)
            self.add_error(None, e)
        return cleaned_data
    
    def __init__(self, *args, **kwargs):
        super(DocumentoForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field, forms.fields.TypedChoiceField):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'


class PersonaEsclavizadaForm(forms.ModelForm):
    
    class Meta:
        model = PersonaEsclavizada
        fields = '__all__'
        widgets = {
            'fecha_nacimiento_factual': forms.CheckboxInput(),
        }
    
    documentos = forms.ModelMultipleChoiceField(
        queryset=Documento.objects.all(),
        required=False,
        widget=autocomplete.ModelSelect2Multiple(url='documento-autocomplete'),
        label='Documentos'
    )
    
    calidades = forms.ModelMultipleChoiceField(
        queryset=Calidades.objects.all(),
        required=False,
        widget=autocomplete.ModelSelect2Multiple(url='calidades-autocomplete'),
        label='Calidades'
    )
    
    hispanizacion = forms.ModelMultipleChoiceField(
        queryset=Hispanizaciones.objects.all(),
        required=False,
        widget=autocomplete.ModelSelect2Multiple(url='hispanizaciones-autocomplete'),
        label='Hispanización'
    )
    
    etnonimos = forms.ModelMultipleChoiceField(
        queryset=Etonimos.objects.all(),
        required=False,
        widget=autocomplete.ModelSelect2Multiple(url='etnonimos-autocomplete'),
        label='Etnónimos'
    )
    
    procedencia = forms.ModelChoiceField(
        queryset=Lugar.objects.all(),
        required=False,
        widget=autocomplete.ModelSelect2(url='lugar-autocomplete'),
        label='Lugar de procedencia'
    )
    
    actividad = forms.ModelChoiceField(
        queryset=Actividades.objects.all(),
        required=False,
        widget=autocomplete.ModelSelect2(url='ocupaciones-autocomplete'),
        label='Ocupación'
    )
    
    ocupacion_categoria = forms.CharField(required=False, label="Categoría ocupación")
    
    conducta = forms.CharField(required=False, label="Registros de conducta")
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if commit:
            instance.save()
            self.save_m2m()
            
            documentos = instance.documentos.all()
            if instance.edad is not None and not instance.fecha_nacimiento and documentos.count() == 1:
                documento = documentos.first()
                if documento and documento.fecha_inicial:
                    calculated_date = CustomBuilders().nacimiento_x_edad(instance.edad, documento.fecha_inicial)
                    instance.fecha_nacimiento = calculated_date
                    instance.fecha_nacimiento_factual = False
                    instance.save()
        
        return instance
    
    def __init__(self, *args, **kwargs):
        super(PersonaEsclavizadaForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            

class PersonaNoEsclavizadaForm(forms.ModelForm):
    
    class Meta:
        model = PersonaNoEsclavizada
        fields = '__all__'
        widgets = {
            'fecha_nacimiento_factual': forms.CheckboxInput(),
        }
    
    documentos = forms.ModelMultipleChoiceField(
        queryset=Documento.objects.all(),
        required=False,
        widget=autocomplete.ModelSelect2Multiple(url='documento-autocomplete'),
        label='Documentos'
    )
    
    calidades = forms.ModelMultipleChoiceField(
        queryset=Calidades.objects.all(),
        required=False,
        widget=autocomplete.ModelSelect2Multiple(url='calidades-autocomplete'),
        label='Calidades'
    )
    
    actividad = forms.ModelChoiceField(
        queryset=Actividades.objects.all(),
        required=False,
        widget=autocomplete.ModelSelect2(url='ocupaciones-autocomplete'),
        label='Ocupación'
    )
    
    ocupacion_categoria = forms.CharField(required=False, label="Categoría ocupación")
    
    rol_evento = forms.ModelMultipleChoiceField(
        queryset=RolEvento.objects.all(),
        required=False,
        widget=autocomplete.ModelSelect2Multiple(url='rolesevento-autocomplete'),
        label='Rol en el evento'
    )
    
    def __init__(self, *args, **kwargs):
        super(PersonaNoEsclavizadaForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

# Relaciones Forms

class PersonaLugarRelForm(forms.ModelForm):
    class Meta:
        model = PersonaLugarRel
        fields = '__all__'

    documento = forms.ModelChoiceField(
        queryset=Documento.objects.all(),
        required=True,
        widget=autocomplete.ModelSelect2(url='documento-autocomplete'),
        label='Documento'
    )

    lugar = forms.ModelChoiceField(
        queryset=Lugar.objects.all(),
        widget=autocomplete.ModelSelect2(url='lugar-autocomplete')
    )
    
    personas = forms.ModelMultipleChoiceField(
        queryset=Persona.objects.all(),
        required=True,
        widget=autocomplete.ModelSelect2Multiple(url='personas-autocomplete'),
        label='Personas relacionadas'
    )
    
    situacion_lugar = forms.ModelChoiceField(
        queryset=SituacionLugar.objects.all(),
        widget=autocomplete.ModelSelect2(url='situacion-autocomplete'),
        label='Sitación en el lugar', required=False,
    )   

    def __init__(self, *args, **kwargs):
        super(PersonaLugarRelForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'


class PersonaRelacionesForm(forms.ModelForm):
    class Meta:
        model = PersonaRelaciones
        fields = '__all__'
        widgets = {
            'naturaleza_relacion': forms.Select(),
            'descripcion_relacion': forms.Textarea(attrs={'rows': 2}),
        }
    
    documento = forms.ModelChoiceField(
        queryset=Documento.objects.all(),
        required=True,
        widget=autocomplete.ModelSelect2(url='documento-autocomplete'),
        label='Documento'
    )
    
    personas = forms.ModelMultipleChoiceField(
        queryset=Persona.objects.all(),
        required=True,
        widget=autocomplete.ModelSelect2Multiple(url='personas-autocomplete'),
        label='Personas relacionadas'
    )
    

# Vocabs Forms

class CalidadesForm(forms.ModelForm):
    
    class Meta:
        model = Calidades
        fields = ['calidad']
        
    def __init__(self, *args, **kwargs):
        super(CalidadesForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

class HispanizacionesForm(forms.ModelForm):
    
    class Meta:
        model = Hispanizaciones
        fields = ['hispanizacion']
        
    def __init__(self, *args, **kwargs):
        super(HispanizacionesForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

class EtnonimosForm(forms.ModelForm):
    
    class Meta:
        model = Etonimos
        fields = ['etonimo']
        
    etonimo = forms.CharField(required=True, label='Etnónimo')
    
    def __init__(self, *args, **kwargs):
        super(EtnonimosForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

class OcupacionesForm(forms.ModelForm):
    
    class Meta:
        model = Actividades
        fields = ['actividad']
        
    def __init__(self, *args, **kwargs):
        super(OcupacionesForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            
class SituacionLugarForm(forms.ModelForm):
    
    class Meta:
        model = SituacionLugar
        fields = ['situacion']
    
    def __init__(self, *args, **kwargs):
        super(SituacionLugarForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

class RolesForm(forms.ModelForm):
    
    class Meta:
        model = RolEvento
        fields = ['rol_evento']
        
    def __init__(self, *args, **kwargs):
        super(RolesForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'