"""
Caching utilities for visualization endpoints.

Provides decorators and helpers for caching expensive API responses based on
filter querystrings, with TTL-based invalidation.
"""

import hashlib
from functools import wraps
from urllib.parse import urlencode

from django.core.cache import cache
from django.http import JsonResponse
from rest_framework.response import Response


def _generate_cache_key(endpoint_name: str, request) -> str:
    """
    Generate a cache key from endpoint name and querystring.

    Cache key format: `viz:{endpoint_name}:{querystring_hash}`
    This ensures different filter combinations have different cache entries.

    Args:
        endpoint_name: Identifier for the visualization endpoint (e.g., 'search_network')
        request: Django request object

    Returns:
        Cache key string
    """
    # Extract and sort querystring to ensure consistent cache keys
    params = sorted(request.query_params.items())
    querystring = urlencode(params) if params else 'default'
    
    # Hash the querystring to keep cache key length reasonable
    querystring_hash = hashlib.md5(querystring.encode()).hexdigest()[:8]
    
    return f'viz:{endpoint_name}:{querystring_hash}'


def cache_visualization(endpoint_name: str, ttl: int):
    """
    Decorator to cache visualization endpoint responses.

    Caches are invalidated based on:
    - Filter querystring (different filters = different cache)
    - TTL (time-to-live in seconds)

    Args:
        endpoint_name: Identifier for the visualization endpoint
        ttl: Cache time-to-live in seconds (e.g., 300 for 5 minutes)

    Usage:
        @cache_visualization('search_network', ttl=300)
        def get(self, request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            cache_key = _generate_cache_key(endpoint_name, request)
            
            # Try to get from cache
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                return Response(cached_response)
            
            # Call the actual view function
            response = view_func(self, request, *args, **kwargs)
            
            # Cache the response data if successful (2xx status)
            if isinstance(response, Response) and 200 <= response.status_code < 300:
                cache.set(cache_key, response.data, ttl)
            
            return response
        
        return wrapper
    return decorator
