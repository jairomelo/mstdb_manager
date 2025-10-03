from django.urls import path, include
from rest_framework.routers import DefaultRouter

# V1beta removed - see API_MIGRATION.md for details

from .v1.views import (DocumentoViewSet, PersonaEsclavizadaViewSet, PersonaLugarRelViewSet, PersonaNoEsclavizadaViewSet, 
                    CorporacionViewSet, PersonaTravelTrajectoryViewSet, SearchAPIView, log_message, LugarAmpliadoViewSet, PersonaPersonaRelViewSet,
                    gender_status_distribution, PlacesPeopleDistribution, whoami, api_login, api_logout,
                    get_csrf_token, BulkIngestAPIView)

# Import V2 views
from .v2 import urls as v2_urls

# V1beta router removed - see API_MIGRATION.md

router_v1 = DefaultRouter()
router_v1.register('documentos', DocumentoViewSet, basename='documentos_api')
router_v1.register('peresclavizadas', PersonaEsclavizadaViewSet, basename='peresclavizadas_api')
router_v1.register('pernoesclavizadas', PersonaNoEsclavizadaViewSet, basename='pernoesclavizadas_api')
router_v1.register('corporaciones', CorporacionViewSet, basename='corporaciones_api')
router_v1.register('lugares', LugarAmpliadoViewSet, basename='lugares_api')
router_v1.register('personas_lugares', PersonaLugarRelViewSet, basename='personas_lugares_api')
router_v1.register('personas_relaciones', PersonaPersonaRelViewSet, basename='personas_relaciones_api')
router_v1.register(f'travel-trajectories', PersonaTravelTrajectoryViewSet, basename='travel-trajectories')

# =============================================================================
# API STRUCTURE:
# - V1beta: REMOVED (October 2025) - was unused experimental version
# - V1: ACTIVE - stable API for existing applications  
# - V2: ACTIVE - performance-optimized API for new features
# See API_MIGRATION.md for full details
# =============================================================================

# v1 paths (stable, maintained for existing applications)
urlpatterns = [
    path('v1/', include(router_v1.urls), name='v1'),
    path('v1/search/', SearchAPIView.as_view(), name='search_api'),
    path('v1/log/', log_message, name='log_message'),
    path('v1/gender-status-distribution/', gender_status_distribution, name='gender_status_distribution'),
    path('v1/places-people-distribution/', PlacesPeopleDistribution.as_view(), name='places_people_distribution'),
    path('v1/login/', api_login, name='api_login'),
    path('v1/logout/', api_logout, name='api_logout'),
    path('v1/whoami/', whoami, name='whoami'),
    path("v1/csrf/", get_csrf_token),
    path('v1/bulk-ingest/', BulkIngestAPIView.as_view(), name='bulk_ingest')
]

# v2 paths (performance-optimized, use for new features)
urlpatterns += [
    path('v2/', include(v2_urls), name='v2')
]
