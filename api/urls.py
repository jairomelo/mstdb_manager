from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from drf_spectacular.views import (SpectacularAPIView, 
                                   SpectacularSwaggerView, 
                                   SpectacularRedocView
                                   )

# =============================================================================
# API HISTORY AND VERSIONING:
# - V1beta: REMOVED (October 2025) - was unused experimental version
# - V1: REMOVED (March 2026) - outdated API for previous applications  
# - V2: ACTIVE - performance-optimized API for new features
# See API_MIGRATION.md for full details
# =============================================================================


# Import V2 views
from .v2 import urls as v2_urls

# Health check endpoint
@api_view(['GET'])
def health_check(request):
    """Health check endpoint for container orchestration"""
    from django.db import connection
    try:
        # Check database connection
        connection.ensure_connection()
        return Response({'status': 'healthy', 'database': 'connected'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'status': 'unhealthy', 'error': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

# v2 paths (performance-optimized, use for new features)
urlpatterns = [
    path('v2/', include(v2_urls), name='v2'),
    path('v2/health/', health_check, name='health_check_v2'),
    path('v2/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('v2/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger'),
    path('v2/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
