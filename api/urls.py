from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import DocumentoViewSet, PersonaEsclavizadaViewSet, SearchAPIView

router = DefaultRouter()
router.register('documentos', DocumentoViewSet, basename='documentos_api')
router.register('peresclavizadas', PersonaEsclavizadaViewSet, basename='peresclavizadas_api')

urlpatterns = router.urls

urlpatterns += [
    path('search/', SearchAPIView.as_view(), name='search_api')
]