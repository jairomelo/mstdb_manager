from typing import Any
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.db import transaction, models
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from dal import autocomplete

from .models import (Lugar, PlaceHistorical, PersonaEsclavizada, PersonaNoEsclavizada, Documento, 
                     Archivo, Calidades, Hispanizaciones, Etonimos, Actividades,
                     PersonaEsclavizadaLugarRel)

from .forms import (LugarForm, LugarHistoria, DocumentoForm, ArchivoForm, PersonaEsclavizadaForm,
                    CalidadesForm, HispanizacionesForm, EtnonimosForm, OcupacionesForm,
                    PersonaEsclavizadaLugarRelForm)

# Create your views here.

def home(request):
    return render(request, 'dbgestor/home.html')

class LugarAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Lugar.objects.all()
        if self.q:
            qs = qs.filter(nombre__icontains=self.q)
            
        return qs

class PersonaEsclavizadaAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = PersonaEsclavizada.objects.all()
        if self.q:
            qs = qs.filter(nombre_normalizado__icontains=self.q)
        return qs

class PersonaNoEsclavizadaAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = PersonaNoEsclavizada.objects.all()
        if self.q:
            qs = qs.filter(nombre_normalizado__icontains=self.q)
        return qs
    
class LugarEventoAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Lugar.objects.all()
        if self.q:
            qs = qs.filter(nombre_lugar__icontains=self.q)
        return qs
    

class DocumentoAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Documento.objects.all()
        if self.q:
            qs = qs.filter(titulo__icontains=self.q)
        return qs


class ArchivoAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Archivo.objects.all()
        if self.q:
            qs = qs.filter(nombre__icontains=self.q)
        return qs
    
class CalidadesAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Calidades.objects.all()
        if self.q:
            qs = qs.filter(nombre__icontains=self.q)
        return qs

class HispanizacionesAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Hispanizaciones.objects.all()
        if self.q:
            qs = qs.filter(nombre__icontains=self.q)
        return qs

class EtnonimosAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Etonimos.objects.all()
        if self.q:
            qs = qs.filter(nombre__icontains=self.q)
        return qs

class OcupacionesAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Actividades.objects.all()
        if self.q:
            qs = qs.filter(nombre__icontains=self.q)
        return qs

# Create Views

class ArchivoCreateView(CreateView):
    model = Archivo
    form_class = ArchivoForm
    template_name = 'dbgestor/Add/archivo.html'
    success_url = reverse_lazy('archivo-browser')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create_archivo'] = context['form']
        context['model_name'] = self.model._meta.model_name
        context['action'] = 'añadir'
        return context
    
    def get_template_names(self):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return ['dbgestor/Modals/archivo_form_only.html']
        return ['dbgestor/Add/archivo.html']
    
    def form_valid(self, form):
        self.object = form.save()

        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data = {
                'archivo_id': self.object.archivo_id,
                'archivo_name': str(self.object) 
            }
            return JsonResponse(data)

        # For non-AJAX requests, redirect as usual
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('archivo-detail', kwargs={'pk': self.object.pk})
        

class DocumentoCreateView(CreateView):
    model = Documento
    form_class = DocumentoForm
    template_name = 'dbgestor/Add/documento.html'
    success_url = reverse_lazy('home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create_documento'] = context['form']
        context['model_name'] = self.model._meta.model_name
        context['action'] = 'añadir'
        return context
    
    def get_template_names(self):
        # Use a different template when the request is AJAX
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return ['dbgestor/Modals/documento_form_only.html']
        return ['dbgestor/Add/documento.html']
    
    def get_template_names(self):
        # Use a different template when the request is AJAX
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return ['dbgestor/Modals/documento_form_only.html']
        return ['dbgestor/Add/documento.html']
    
    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        self.object = form.save()

        # Check if the request is AJAX
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Return a JsonResponse with Documento data
            data = {
                'documento_id': self.object.documento_id,
                'documento_name': str(self.object)  # Adjust the name as per your model's __str__ method
            }
            return JsonResponse(data)

        # For non-AJAX requests, redirect as usual
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('documento-detail', kwargs={'pk': self.object.pk})



class LugarCreateView(CreateView):
    model = Lugar
    form_class = LugarForm
    template_name = 'dbgestor/Add/lugar.html'
    success_url = reverse_lazy('home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create_lugar'] = context['form']
        context['model_name'] = self.model._meta.model_name
        context['action'] = 'añadir'
        return context
    
    def get_template_names(self):
        
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return ['dbgestor/Modals/lugar_form_only.html']
        return ['dbgestor/Add/lugar.html']
    
    def form_valid(self, form):
        self.object = form.save()

        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data = {
                'lugar_id': self.object.id,
                'lugar_name': str(self.object)  
            }
            return JsonResponse(data)

        return super().form_valid(form)
    
    def get_success_url(self):
        #return reverse_lazy('lugar-detail', kwargs={'pk': self.object.pk})
        return reverse_lazy('home')
    

class PersonaEsclavizadaCreateView(CreateView):
    model = PersonaEsclavizada
    form_class = PersonaEsclavizadaForm
    template_name = 'dbgestor/Add/peresclavizada.html'
    success_url = reverse_lazy('personasesclavizadas-browse')
    
    def get_initial(self) -> dict[str, Any]:
        initial = super().get_initial()
        
        documento_initial = self.request.GET.get('documento_initial')
        if documento_initial:
            initial['documentos'] = documento_initial
        
        return initial


# create views for RElations

class PersonaEsclavizadaLugarRelCreateView(CreateView):
    model = PersonaEsclavizadaLugarRel
    form_class = PersonaEsclavizadaLugarRelForm
    template_name = 'dbgestor/Relaciones/personaesclavizada_x_lugar.html'
    success_url = reverse_lazy('documento-browse')

    def get_initial(self) -> dict[str, Any]:
        initial = super().get_initial()
        
        documento_initial = self.request.GET.get('documento_initial')
        personaesclavizada_initial = self.request.GET.get('personaesclavizada_initial')
        if documento_initial:
            initial['documento'] = documento_initial
        if personaesclavizada_initial:
            initial['personaesclavizada'] = personaesclavizada_initial
        return initial

# Create views for  Vocabs
class CalidadesCreateView(CreateView):
    model = Calidades
    form_class = CalidadesForm
    template_name = 'dbgestor/Vocab/calidad.html'
    success_url = reverse_lazy('documento-browse')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create_calidad'] = context['form']
        context['model_name'] = self.model._meta.model_name
        context['action'] = 'añadir'
        return context
    
    def get_template_names(self):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return ['dbgestor/Modals/calidad.html']
        return ['dbgestor/Vocab/calidad.html']
    
    def form_valid(self, form):
        self.object = form.save()

        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data = {
                'calidad_id': self.object.calidad_id,
                'calidad_name': str(self.object) 
            }
            return JsonResponse(data)

        # For non-AJAX requests, redirect as usual
        return super().form_valid(form)

class HispanizacionesCreateView(CreateView):
    model = Hispanizaciones
    form_class = HispanizacionesForm
    template_name = 'dbgestor/Vocab/hispanizacion.html'
    success_url = reverse_lazy('documento-browse')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create_hispanizacion'] = context['form']
        context['model_name'] = self.model._meta.model_name
        context['action'] = 'añadir'
        return context
    
    def get_template_names(self):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return ['dbgestor/Modals/hispanizacion.html']
        return ['dbgestor/Vocab/hispanizacion.html']
    
    def form_valid(self, form):
        self.object = form.save()

        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data = {
                'hispanizacion_id': self.object.hispanizacion_id,
                'hispanizacion_name': str(self.object) 
            }
            return JsonResponse(data)

        # For non-AJAX requests, redirect as usual
        return super().form_valid(form)

class EtnonimosCreateView(CreateView):
    model = Etonimos
    form_class = EtnonimosForm
    template_name = 'dbgestor/Vocab/etnonimo.html'
    success_url = reverse_lazy('documento-browse')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create_etnonimo'] = context['form']
        context['model_name'] = self.model._meta.model_name
        context['action'] = 'añadir'
        return context
    
    def get_template_names(self):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return ['dbgestor/Modals/etnonimo.html']
        return ['dbgestor/Vocab/etnonimo.html']
    
    def form_valid(self, form):
        self.object = form.save()

        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data = {
                'etnonimo_id': self.object.etonimo_id,
                'etnonimo_name': str(self.object) 
            }
            return JsonResponse(data)

        # For non-AJAX requests, redirect as usual
        return super().form_valid(form)

class OcupacionesCreateView(CreateView):
    model = Actividades
    form_class = OcupacionesForm
    template_name = 'dbgestor/Vocab/ocupacion.html'
    success_url = reverse_lazy('documento-browse')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create_ocupacion'] = context['form']
        context['model_name'] = self.model._meta.model_name
        context['action'] = 'añadir'
        return context
    
    def get_template_names(self):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return ['dbgestor/Modals/ocupacion.html']
        return ['dbgestor/Vocab/ocupacion.html']
    
    def form_valid(self, form):
        self.object = form.save()

        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data = {
                'ocupacion_id': self.object.actividad_id,
                'ocupacion_name': str(self.object) 
            }
            return JsonResponse(data)

        # For non-AJAX requests, redirect as usual
        return super().form_valid(form)

# Browse Views

class ArchivoBrowse(ListView):
    model = Archivo
    template_name = 'dbgestor/Browse/archivos.html'

    def get_queryset(self):
        queryset = super().get_queryset()
        sort = self.request.GET.get('sort', 'updated_at')
        if sort not in ['archivo', 'created_at', 'titulo', 'tipo_documento', 'tipo_udc']:
            sort = 'updated_at'
        
        search_query = self.request.GET.get('q', None)
        if search_query:
            queryset = queryset.filter(
                Q(titulo__icontains=search_query) | 
                Q(fondo__icontains=search_query)
            )
        
        return queryset.order_by(sort)

class DocumentoBrowse(ListView):
    model = Documento
    template_name = 'dbgestor/Browse/documentos.html'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        sort = self.request.GET.get('sort', 'updated_at')
        if sort not in ['archivo', 'created_at', 'titulo', 'tipo_documento', 'tipo_udc']:
            sort = 'updated_at'
        
        search_query = self.request.GET.get('q', None)
        if search_query:
            queryset = queryset.filter(
                Q(titulo__icontains=search_query) | 
                Q(fondo__icontains=search_query)
            )
        
        return queryset.order_by(sort)

class PersonaEsclavizadaBrowse(ListView):
    model = PersonaEsclavizada
    template_name = 'dbgestor/Browse/personasesclavizadas.html'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        sort = self.request.GET.get('sort', 'updated_at')
        if sort not in ['nombres', 'created_at', 'apellidos', 'nombre_normalizado']:
            sort = 'updated_at'
        
        search_query = self.request.GET.get('q', None)
        if search_query:
            queryset = queryset.filter(
                Q(nombres__icontains=search_query) | 
                Q(apellidos__icontains=search_query) |
                Q(nombre_normalizado__icontains=search_query)
            )
        
        return queryset.order_by(sort)

# Detail views

class ArchivoDetailView(DetailView):
    model = Archivo
    template_name = 'dbgestor/Detail/archivo.html'

class DocumentoDetailView(DetailView):
    model = Documento
    template_name = 'dbgestor/Detail/documento.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        last_history = self.object.history.first()
        history_records = self.object.history.all()
        context['history_records'] = history_records
        
        documento = self.get_object()
        
        peresclavizadas = PersonaEsclavizada.objects.filter(
            models.Q(
                documentos=documento
            )
        )
        
        personaesclavizadalugarrel = PersonaEsclavizadaLugarRel.objects.filter(
            models.Q(
                documento=documento
            )
        )
        
        context['peresclavizadas'] = peresclavizadas
        context['personaesclavizadalugarrel'] = personaesclavizadalugarrel
        
        last_updated_user = None
        if last_history:
            last_updated_user = last_history.history_user
        
        context['last_updated_user'] = last_updated_user
        
        return context

class PersonaEsclavizadaDetailView(DetailView):
    model = PersonaEsclavizada
    template_name = 'dbgestor/Detail/personaesclavizada.html'

# Update views

class ArchivoUpdateView(UpdateView):
    model = Archivo
    form_class = ArchivoForm
    template_name = 'dbgestor/Add/archivo.html'
    success_url = reverse_lazy('archivo-browse')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['model_name'] = self.model._meta.model_name
        context['action'] = 'editar'
        return context
    
    def get_form_kwargs(self):
        kwargs = super(ArchivoUpdateView, self).get_form_kwargs()
        
        return kwargs
    
class DocumentoUpdateView(UpdateView):
    model = Documento
    form_class = DocumentoForm
    template_name = 'dbgestor/Add/documento.html' 
    success_url = reverse_lazy('documento-browse')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['model_name'] = self.model._meta.model_name
        context['action'] = 'editar'
        return context
    
    def get_form_kwargs(self):
        kwargs = super(DocumentoUpdateView, self).get_form_kwargs()
        
        return kwargs


class PersonaEsclavizadaUpdateView(UpdateView):
    model = PersonaEsclavizada
    form_class = PersonaEsclavizadaForm
    template_name = 'dbgestor/Add/personaesclavizada.html' 
    success_url = reverse_lazy('personasesclavizadas-browse')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['model_name'] = self.model._meta.model_name
        context['action'] = 'editar'
        return context
    
    def get_form_kwargs(self):
        kwargs = super(PersonaEsclavizadaUpdateView, self).get_form_kwargs()
        
        return kwargs

# Delete views    

class ArchivoDeleteView(DeleteView):
    model = Archivo
    template_name = 'dbgestor/Base/archivo_confirm_delete.html'
    success_url = reverse_lazy('archivo-browse')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['model_name'] = self.model._meta.model_name
        context['action'] = 'borrar'
        return context
    
class DocumentoDeleteView(DeleteView):
    model = Documento
    template_name = 'dbgestor/Base/documento_confirm_delete.html'
    success_url = reverse_lazy('documento-browse')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['model_name'] = self.model._meta.model_name
        context['action'] = 'borrar'
        return context
    

class PersonaEsclavizadaDeleteView(DeleteView):
    model = Documento
    template_name = 'dbgestor/Base/personaesclavizada_confirm_delete.html'
    success_url = reverse_lazy('personasesclavizadas-browse')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['model_name'] = self.model._meta.model_name
        context['action'] = 'borrar'
        return context