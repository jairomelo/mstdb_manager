from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ArchivoViewSet, DocumentoViewSet, PersonaEsclavizadaViewSet, PersonaNoEsclavizadaViewSet,
    LugarViewSet, CorporacionViewSet, PersonaRelacionesViewSet, PersonaLugarRelViewSet,
    PersonaTravelTrajectoryViewSet, SearchAPIView, get_csrf_token
)

# Create router for V2 API
router_v2 = DefaultRouter()

# Register all ViewSets
router_v2.register('archivos', ArchivoViewSet, basename='archivos_api_v2')
router_v2.register('documentos', DocumentoViewSet, basename='documentos_api_v2')
router_v2.register('personas-esclavizadas', PersonaEsclavizadaViewSet, basename='personas_esclavizadas_api_v2')
router_v2.register('personas-no-esclavizadas', PersonaNoEsclavizadaViewSet, basename='personas_no_esclavizadas_api_v2')
router_v2.register('lugares', LugarViewSet, basename='lugares_api_v2')
router_v2.register('corporaciones', CorporacionViewSet, basename='corporaciones_api_v2')
router_v2.register('relaciones-personas', PersonaRelacionesViewSet, basename='relaciones_personas_api_v2')
router_v2.register('relaciones-lugares', PersonaLugarRelViewSet, basename='relaciones_lugares_api_v2')
router_v2.register('travel-trajectories', PersonaTravelTrajectoryViewSet, basename='travel_trajectories_api_v2')

# URL patterns for V2
urlpatterns = [
    # Router URLs (includes CRUD endpoints for all entities)
    path('', include(router_v2.urls)),
    
    # Custom endpoints
    path('search/', SearchAPIView.as_view(), name='search_api_v2'),
    path('csrf/', get_csrf_token, name='csrf_token_v2'),
]