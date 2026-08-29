"""Server-side proxy for Carto basemap tiles.

Keeps CARTO_API private: the SPA requests tiles from this endpoint and the key
is appended only here, server-side. Validation + rate limiting + caching bound
abuse and upstream cost.
"""
import time

import requests
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseBadRequest

# Whitelist of layers this proxy is willing to serve.
ALLOWED_LAYERS = {'light_nolabels'}
CARTO_SUBDOMAINS = ['a', 'b', 'c', 'd']
MAX_ZOOM = 22
TILE_CACHE_TTL = 60 * 60 * 24 * 7  # tiles are immutable; cache for a week
RATE_LIMIT_PER_MINUTE = 120
REQUEST_TIMEOUT = 10


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def _rate_limited(ip):
    key = f'carto_tile_rl:{ip}:{int(time.time()) // 60}'
    try:
        count = cache.incr(key)
    except Exception:
        count = None
    if count is None:
        # cache unavailable (IGNORE_EXCEPTIONS) -> fail open
        try:
            cache.set(key, 1, timeout=120)
        except Exception:
            pass
        return False
    return count > RATE_LIMIT_PER_MINUTE


def carto_tile_proxy(request, layer, z, x, y):
    if layer not in ALLOWED_LAYERS:
        return HttpResponseBadRequest('Unsupported layer')
    if not (0 <= z <= MAX_ZOOM):
        return HttpResponseBadRequest('Zoom out of range')
    edge = 1 << z
    if not (0 <= x < edge and 0 <= y < edge):
        return HttpResponseBadRequest('Tile out of range')

    cache_key = f'carto_tile:{layer}:{z}:{x}:{y}'
    body = cache.get(cache_key)
    if body is None:
        if _rate_limited(_client_ip(request)):
            return HttpResponse('Too many requests', status=429)
        subdomain = CARTO_SUBDOMAINS[(x * 7 + y * 13 + z) % len(CARTO_SUBDOMAINS)]
        url = (
            f'https://{subdomain}.basemaps.cartocdn.com/{layer}/{z}/{x}/{y}.png'
        )
        try:
            upstream = requests.get(
                url, params={'key': settings.CARTO_API}, timeout=REQUEST_TIMEOUT
            )
            upstream.raise_for_status()
        except requests.RequestException:
            return HttpResponse('Upstream tile error', status=502)
        body = upstream.content
        cache.set(cache_key, body, TILE_CACHE_TTL)

    response = HttpResponse(body, content_type='image/png')
    response['Cache-Control'] = 'public, max-age=86400, stale-while-revalidate=604800'
    return response
