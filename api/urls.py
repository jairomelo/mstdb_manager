from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (DocumentoViewSet, PersonaEsclavizadaViewSet, PersonaNoEsclavizadaViewSet, 
                    CorporacionViewSet, SearchAPIView, log_message)

router = DefaultRouter()
router.register('documentos', DocumentoViewSet, basename='documentos_api')
router.register('peresclavizadas', PersonaEsclavizadaViewSet, basename='peresclavizadas_api')
router.register('pernoesclavizadas', PersonaNoEsclavizadaViewSet, basename='pernoesclavizadas_api')
router.register('corporaciones', CorporacionViewSet, basename='corporaciones_api')

urlpatterns = router.urls

urlpatterns += [
    path('search/', SearchAPIView.as_view(), name='search_api'),
    path('log', log_message, name='log_message')
]