# pages/urls.py
from django.urls import path
from .views import home, LugarCreateView, LugarAutocomplete, PersonaEsclavizadaAutocomplete
from .views import (PersonaNoEsclavizadaAutocomplete, DocumentoAutocomplete, LugarEventoAutocomplete, 
                    CalidadesPersonaEsclavizadaAutocomplete, CalidadesPersonasNoEsclavizadasAutocomplete,
                    ArchivoAutocomplete, SituacionLugarAutocomplete, TipoDocumentalAutocomplete,
                    TipoLugarAutocomplete, RolEventoAutocomplete,
                    DocumentoCreateView, ArchivoCreateView, DocumentoBrowse,
                    DocumentoDetailView, DocumentoUpdateView, DocumentoDeleteView, ArchivoBrowse,
                    TotalBrowseView,
                    ArchivoDetailView, ArchivoUpdateView, ArchivoDeleteView, PersonaEsclavizadaCreateView,
                    PersonaNoEsclavizadaCreateView, PersonaNoEsclavizadaBrowse, PersonaNoEsclavizadaDeleteView,
                    PersonaNoEsclavizadaDetailView, PersonaNoEsclavizadaUpdateView,
                    CalidadesAutocomplete, HispanizacionesAutocomplete, EtnonimosAutocomplete,
                    EtnonimosCreateView, HispanizacionesCreateView, CalidadesCreateView,
                    OcupacionesCreateView, OcupacionesAutocomplete,
                    PersonaEsclavizadaBrowse, PersonaEsclavizadaDeleteView, PersonaEsclavizadaDetailView,
                    PersonaEsclavizadaUpdateView, RolesCreateView,
                    PersonaLugarRelCreateView, PersonaPersonaRelCreateView, PersonaAutocomplete,
                    SituacionLugarCreateView,
                    DeletePersonaRelacionesView, DeletePersonaLugarRelView)


urlpatterns = [
    path("", home, name="home"),
    path('Add/lugar/', LugarCreateView.as_view(), name='lugar-new'),
    path('lugar-autocomplete/', LugarAutocomplete.as_view(), name='lugar-autocomplete'),
    path('Add/documento/', DocumentoCreateView.as_view(), name='documento-new'),
    path('Add/archivo/', ArchivoCreateView.as_view(), name='archivo-new'),
    path('Add/personaesclavizada/', PersonaEsclavizadaCreateView.as_view(), name='personaesclavizada-new'),
    path('Add/personanoesclavizada/', PersonaNoEsclavizadaCreateView.as_view(), name='personanoesclavizada-new'),
    # relations
    path('Add/peresclavizada_x_lugar/', PersonaLugarRelCreateView.as_view(), name='persona_x_lugar-new'),
    path('Add/persona_x_persona/', PersonaPersonaRelCreateView.as_view(), name='persona_x_persona-new'),
    # vocabs create
    path('Add/voc/calidad/', CalidadesCreateView.as_view(), name='calidad-new'),
    path('Add/voc/hispanizacion/', HispanizacionesCreateView.as_view(), name='hispanizacion-new'),
    path('Add/voc/etnonimo/', EtnonimosCreateView.as_view(), name='etnonimo-new'),
    path('Add/voc/ocupacion/', OcupacionesCreateView.as_view(), name='ocupacion-new'),
    path('Add/voc/rol/', RolesCreateView.as_view(), name='rol-new'),
    path('Add/voc/situacion/', SituacionLugarCreateView.as_view(), name='situacion-new'),
    # browse views
    path('Browse/archivos', ArchivoBrowse.as_view(), name="archivo-browse"),
    path('Browse/documentos', DocumentoBrowse.as_view(), name="documento-browse"),
    path('Browse/personasesclavizadas', PersonaEsclavizadaBrowse.as_view(), name="personasesclavizadas-browse"),
    path('Browse/personasnoesclavizadas', PersonaNoEsclavizadaBrowse.as_view(), name="personasnoesclavizadas-browse"),
    path('Browse/vistaconsolidada', TotalBrowseView.as_view(), name='vista-consolidada'),
    # detail views
    path('Detail/archivo/<int:pk>', ArchivoDetailView.as_view(), name='archivo-detail'),
    path('Detail/documento/<int:pk>', DocumentoDetailView.as_view(), name='documento-detail'),
    path('Detail/personaesclavizada/<int:pk>', PersonaEsclavizadaDetailView.as_view(), name='personaesclavizada-detail'),
    path('Detail/personanoesclavizada/<int:pk>', PersonaNoEsclavizadaDetailView.as_view(), name='personanoesclavizada-detail'),

    # update views
    path('Update/archivo/<int:pk>', ArchivoUpdateView.as_view(), name='archivo-update'),
    path('Update/documento/<int:pk>', DocumentoUpdateView.as_view(), name='documento-update'),
    path('Update/personaesclavizada/<int:pk>', PersonaEsclavizadaUpdateView.as_view(), name='personaesclavizada-update'),
    path('Update/personanoesclavizada/<int:pk>', PersonaNoEsclavizadaUpdateView.as_view(), name='personanoesclavizada-update'),
    # delete views
    path('archivo/<int:pk>/delete/', ArchivoDeleteView.as_view(), name='archivo-delete'),
    path('documento/<int:pk>/delete/', DocumentoDeleteView.as_view(), name='documento-delete'),
    path('personaesclavizada/<int:pk>/delete/', PersonaEsclavizadaDeleteView.as_view(), name='personaesclavizada-delete'),
    path('personanoesclavizada/<int:pk>/delete/', PersonaNoEsclavizadaDeleteView.as_view(), name='personanoesclavizada-delete'),
    # autocompleters
    path('persona-esclavizada-autocomplete/', PersonaEsclavizadaAutocomplete.as_view(), name='personaesclavizada-autocomplete'),
    path('persona-no-esclavizada-autocomplete/', PersonaNoEsclavizadaAutocomplete.as_view(), name='persona-no-esclavizada-autocomplete'),
    path('persona-autocomplete/', PersonaAutocomplete.as_view(), name='personas-autocomplete'),
    path('lugar-autocomplete/', LugarEventoAutocomplete.as_view(), name='lugar-autocomplete'),
    path('documento-autocomplete/', DocumentoAutocomplete.as_view(), name='documento-autocomplete'),
    path('archivo-autocomplete/', ArchivoAutocomplete.as_view(), name='archivo-autocomplete'),
    path('calidad-autocomplete/', CalidadesAutocomplete.as_view(), name='calidades-autocomplete'),
    path('calidades-personas-esclavizadas/', CalidadesPersonaEsclavizadaAutocomplete.as_view(), name='calidades-personas-esclavizadas'),
    path('calidades-personas-no-esclavizadas/', CalidadesPersonasNoEsclavizadasAutocomplete.as_view(), name='calidades-personas-no-esclavizadas'),
    path('hispanizacion-autocomplete/', HispanizacionesAutocomplete.as_view(), name='hispanizaciones-autocomplete'),
    path('etnonimo-autocomplete/', EtnonimosAutocomplete.as_view(), name='etnonimos-autocomplete'),
    path('ocupacion-autocomplete/', OcupacionesAutocomplete.as_view(), name='ocupaciones-autocomplete'),
    path('situacion-autocomplete', SituacionLugarAutocomplete.as_view(), name='situacion-autocomplete'),
    path('tipodocumental-autocomplete', TipoDocumentalAutocomplete.as_view(), name='tiposdocumentales-autocomplete'),
    path('tipolugar-autocomplete', TipoLugarAutocomplete.as_view(), name='tiposlugar-autocomplete'),
    path('rolesevento-autocomplete', RolEventoAutocomplete.as_view(), name='rolesevento-autocomplete'),
    # testing
    path('personarel/delete/<int:pk>/', DeletePersonaRelacionesView.as_view(), name='delete-personarel'),
    path('personalugar/delete/<int:pk>/', DeletePersonaLugarRelView.as_view(), name='delete-personalugarrel'),
]