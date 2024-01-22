from django.shortcuts import render
from django.urls import reverse_lazy
from django.db import transaction, models
from django.http import HttpResponse, JsonResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from dal import autocomplete

from .models import Lugar, PlaceHistorical

from .forms import LugarForm, LugarHistoria

# Create your views here.

def home(request):
    return render(request, 'dbgestor/home.html')

class LugarAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Lugar.objects.all()
        if self.q:
            qs = qs.filter(nombre__icontains=self.q)
            
        return qs

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