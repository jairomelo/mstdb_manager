# pages/urls.py
from django.urls import path
from .views import CoporacionCreateView, CorporacionBrowse, CorporacionDeleteView, CorporacionDetailView, CorporacionUpdateView, DeleteRolEventoView, PersonaRolEventoCreateView, TipoDocumentalsCreateView, home, associate_persona_documento, associate_institucion_documento, InstitucionAutocomplete
from .views import (
    ArchivoAutocomplete, ArchivoBrowse, ArchivoCreateView, ArchivoDeleteView, ArchivoDetailView,
    ArchivoUpdateView, CalidadesAutocomplete, CalidadesCreateView, CalidadesPersonaEsclavizadaAutocomplete,
    CalidadesPersonasNoEsclavizadasAutocomplete, DeletePersonaLugarRelView, DeletePersonaRelacionesView,
    DocumentoAutocomplete, DocumentoBrowse, DocumentoCreateView, DocumentoDeleteView, DocumentoDetailView,
    DocumentoUpdateView, EtnonimosAutocomplete, EtnonimosCreateView, HispanizacionesAutocomplete,
    HispanizacionesCreateView, LugarAutocomplete, LugarCreateView, OcupacionesAutocomplete, 
    OcupacionesCreateView, PersonaAutocomplete, PersonaEsclavizadaBrowse, PersonaEsclavizadaCreateView, PersonaEsclavizadaDeleteView,
    PersonaEsclavizadaAutocomplete, PersonaEsclavizadaDetailView, PersonaEsclavizadaUpdateView, PersonaLugarRelCreateView, PersonaLugarRelUpdateView,
    PersonaNoEsclavizadaAutocomplete, PersonaNoEsclavizadaBrowse, PersonaNoEsclavizadaCreateView,
    PersonaNoEsclavizadaDeleteView, PersonaNoEsclavizadaDetailView, PersonaNoEsclavizadaUpdateView,
    PersonaPersonaRelCreateView, PersonaRelacionesUpdateView, RolesCreateView, RolEventoAutocomplete,
    SituacionLugarAutocomplete, SituacionLugarCreateView, TipoDocumentalAutocomplete, TipoLugarAutocomplete,
    TotalBrowseView,PersonaDeleteView,ConfirmRemovePersonaDocumento, TiposInstitucionAutocomplete,
    TipoInstitucionCreateView
)



urlpatterns = [
    path("", TotalBrowseView.as_view(), name="home"),
    path('remove_persona_documento/<int:persona_id>/<int:documento_id>/', ConfirmRemovePersonaDocumento.as_view(), name='remove_persona_documento'),
    path('Add/lugar/', LugarCreateView.as_view(), name='lugar-new'),
    path('Add/documento/', DocumentoCreateView.as_view(), name='documento-new'),
    path('Add/archivo/', ArchivoCreateView.as_view(), name='archivo-new'),
    path('Add/personaesclavizada/', PersonaEsclavizadaCreateView.as_view(), name='personaesclavizada-new'),
    path('Add/personanoesclavizada/', PersonaNoEsclavizadaCreateView.as_view(), name='personanoesclavizada-new'),
    path('Add/institucion/', CoporacionCreateView.as_view(), name='institucion_new'),
    # relations
    path('Add/peresclavizada_x_lugar/', PersonaLugarRelCreateView.as_view(), name='persona_x_lugar-new'),
    path('Add/persona_x_persona/', PersonaPersonaRelCreateView.as_view(), name='persona_x_persona-new'),
    path('Add/rol_evento/', PersonaRolEventoCreateView.as_view(), name='rol_evento_new'),
    # vocabs create
    path('Add/voc/tipo_documento/', TipoDocumentalsCreateView.as_view(), name='tipo_documento-new'),
    path('Add/voc/tipo_institucion/', TipoInstitucionCreateView.as_view(), name='tipo_institucion_new'),
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
    path('Browse/instituciones', CorporacionBrowse.as_view(), name='instituciones_browse'),
    # detail views
    path('Detail/archivo/<int:pk>', ArchivoDetailView.as_view(), name='archivo-detail'),
    path('Detail/documento/<int:pk>', DocumentoDetailView.as_view(), name='documento-detail'),
    path('Detail/personaesclavizada/<int:pk>', PersonaEsclavizadaDetailView.as_view(), name='personaesclavizada_detail'),
    path('Detail/personanoesclavizada/<int:pk>', PersonaNoEsclavizadaDetailView.as_view(), name='personanoesclavizada_detail'),
    path('Detail/institucion/<int:pk>', CorporacionDetailView.as_view(), name='institucion_detail'),

    # update views
    path('Update/archivo/<int:pk>', ArchivoUpdateView.as_view(), name='archivo-update'),
    path('Update/documento/<int:pk>', DocumentoUpdateView.as_view(), name='documento-update'),
    path('Update/personaesclavizada/<int:pk>', PersonaEsclavizadaUpdateView.as_view(), name='personaesclavizada-update'),
    path('Update/personanoesclavizada/<int:pk>', PersonaNoEsclavizadaUpdateView.as_view(), name='personanoesclavizada-update'),
    path('Update/institucion/<int:pk>', CorporacionUpdateView.as_view(), name='institucion_update'),
    path('Update/persona_x_lugar/<int:pk>', PersonaLugarRelUpdateView.as_view(), name='persona_x_lugar-update'),
    path('Update/persona_x_persona/<int:pk>', PersonaRelacionesUpdateView.as_view(), name='persona_x_persona-update'),
    path('Update/persona_x_documentos/', associate_persona_documento, name='persona_x_documentos'),
    path('Update/institucion_x_documentos/', associate_institucion_documento, name='institucion_x_documentos'),
    # delete views
    path('archivo/<int:pk>/delete/', ArchivoDeleteView.as_view(), name='archivo-delete'),
    path('documento/<int:pk>/delete/', DocumentoDeleteView.as_view(), name='documento-delete'),
    path('persona/<int:pk>/delete/', PersonaDeleteView.as_view(), name='persona-delete'),
    path('personaesclavizada/<int:pk>/delete/', PersonaEsclavizadaDeleteView.as_view(), name='personaesclavizada-delete'),
    path('personanoesclavizada/<int:pk>/delete/', PersonaNoEsclavizadaDeleteView.as_view(), name='personanoesclavizada-delete'),
    path('institucion/<int:pk>/delete/', CorporacionDeleteView.as_view(), name='institucion_delete'),
    path('rolevento/<int:pk>/delete/', DeleteRolEventoView.as_view(), name='rol_delete'),
    # autocompleters
    path('lugar-autocomplete/', LugarAutocomplete.as_view(), name='lugar-autocomplete'),
    path('persona-esclavizada-autocomplete/', PersonaEsclavizadaAutocomplete.as_view(), name='personaesclavizada-autocomplete'),
    path('persona-no-esclavizada-autocomplete/', PersonaNoEsclavizadaAutocomplete.as_view(), name='persona-no-esclavizada-autocomplete'),
    path('persona-autocomplete/', PersonaAutocomplete.as_view(), name='personas-autocomplete'),
    path('institucion_autocomplete/', InstitucionAutocomplete.as_view(), name='institucion-autocomplete'),
    path('documento-autocomplete/', DocumentoAutocomplete.as_view(), name='documento-autocomplete'),
    path('archivo-autocomplete/', ArchivoAutocomplete.as_view(), name='archivo-autocomplete'),
    path('calidad-autocomplete/', CalidadesAutocomplete.as_view(), name='calidades-autocomplete'),
    path('calidades-personas-esclavizadas/', CalidadesPersonaEsclavizadaAutocomplete.as_view(), name='calidades-personas-esclavizadas'),
    path('calidades-personas-no-esclavizadas/', CalidadesPersonasNoEsclavizadasAutocomplete.as_view(), name='calidades-personas-no-esclavizadas'),
    path('hispanizacion-autocomplete/', HispanizacionesAutocomplete.as_view(), name='hispanizaciones-autocomplete'),
    path('etnonimo-autocomplete/', EtnonimosAutocomplete.as_view(), name='etnonimos-autocomplete'),
    path('ocupacion-autocomplete/', OcupacionesAutocomplete.as_view(), name='ocupaciones-autocomplete'),
    path('situacion-autocomplete/', SituacionLugarAutocomplete.as_view(), name='situacion-autocomplete'),
    path('tipodocumental-autocomplete/', TipoDocumentalAutocomplete.as_view(), name='tiposdocumentales-autocomplete'),
    path('tipolugar-autocomplete/', TipoLugarAutocomplete.as_view(), name='tiposlugar-autocomplete'),
    path('rolesevento-autocomplete/', RolEventoAutocomplete.as_view(), name='rolesevento-autocomplete'),
    path('tiposintitucion-autocomplete/', TiposInstitucionAutocomplete.as_view(), name='tiposintitucion-autocomplete'),
    # testing
    path('personarel/delete/<int:pk>/', DeletePersonaRelacionesView.as_view(), name='delete-personarel'),
    path('personalugar/delete/<int:pk>/', DeletePersonaLugarRelView.as_view(), name='delete-personalugarrel'),
]