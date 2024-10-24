from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .v1beta.views import (DocumentoViewSet as DocumentoViewSetBeta,
                            PersonaEsclavizadaViewSet as PersonaEsclavizadaViewSetBeta,
                            PersonaNoEsclavizadaViewSet as PersonaNoEsclavizadaViewSetBeta,
                            CorporacionViewSet as CorporacionViewSetBeta,
                            LugarAmpliadoViewSet as LugarAmpliadoViewSetBeta,
                            log_message as log_message_beta,
                            SearchAPIView as SearchAPIViewBeta
                            )

from .v1.views import (DocumentoViewSet, PersonaEsclavizadaViewSet, PersonaNoEsclavizadaViewSet, 
                    CorporacionViewSet, SearchAPIView, log_message, LugarAmpliadoViewSet)

router_v1beta = DefaultRouter()
router_v1beta.register('documentos', DocumentoViewSetBeta, basename='documentos_api_beta')
router_v1beta.register('peresclavizadas', PersonaEsclavizadaViewSetBeta, basename='peresclavizadas_api_beta')
router_v1beta.register('pernoesclavizadas', PersonaNoEsclavizadaViewSetBeta, basename='pernoesclavizadas_api_beta')
router_v1beta.register('corporaciones', CorporacionViewSetBeta, basename='corporaciones_api_beta')
router_v1beta.register('lugares', LugarAmpliadoViewSetBeta, basename='lugares_api_beta')

router_v1 = DefaultRouter()
router_v1.register('documentos', DocumentoViewSet, basename='documentos_api')
router_v1.register('peresclavizadas', PersonaEsclavizadaViewSet, basename='peresclavizadas_api')
router_v1.register('pernoesclavizadas', PersonaNoEsclavizadaViewSet, basename='pernoesclavizadas_api')
router_v1.register('corporaciones', CorporacionViewSet, basename='corporaciones_api')
router_v1.register('lugares', LugarAmpliadoViewSet, basename='lugares_api')

# beta paths
urlpatterns = [
    path('v1-beta/', include(router_v1beta.urls), name='v1beta'),
    path('v1-beta/search/', SearchAPIViewBeta.as_view(), name='search_api_beta'),
    path('v1-beta/log/', log_message_beta, name='log_message_beta')
]

# v1 paths
urlpatterns += [
    path('v1/', include(router_v1.urls), name='v1'),
    path('v1/search/', SearchAPIView.as_view(), name='search_api'),
    path('v1/log/', log_message, name='log_message'),
]
