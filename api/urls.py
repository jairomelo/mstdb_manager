from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import DocumentoViewSet

router = DefaultRouter()
router.register('documentos', DocumentoViewSet, basename='documentos')

urlpatterns = router.urls
