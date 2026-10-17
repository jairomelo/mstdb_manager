"""Load-test-gated throttle bypass.

Production stress tests hit the read API from a single source IP, which trips
DRF's global ``anon`` (60/min) and ``user`` (300/min) throttles within seconds.
Raising those limits for everyone would weaken normal protection, so instead a
matching ``X-Loadtest-Token`` header skips rate limiting only.

The bypass is inert unless ``LOADTEST_TOKEN`` is set to a non-empty value in the
environment, so production behaves exactly as before by default. It is a
deliberate, reversible release: set the token for the test window, clear it
(and redeploy) afterwards. The token is compared with ``hmac.compare_digest`` to
avoid leaking it through timing.
"""

import hmac

from django.conf import settings
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

LOADTEST_TOKEN_HEADER = 'X-Loadtest-Token'
LOADTEST_TOKEN_META_KEY = 'HTTP_X_LOADTEST_TOKEN'


def _configured_token() -> str:
    return getattr(settings, 'LOADTEST_TOKEN', '') or ''


def is_loadtest_request(request) -> bool:
    """Return True when the request carries the configured load-test token.

    Always False when ``LOADTEST_TOKEN`` is unset/empty, which keeps the bypass
    disabled in normal operation.
    """
    expected = _configured_token()
    if not expected:
        return False

    provided = request.META.get(LOADTEST_TOKEN_META_KEY, '')
    if not provided:
        return False

    return hmac.compare_digest(str(provided), str(expected))


class LoadtestBypassMixin:
    """Short-circuit the rate limit for requests presenting the bypass token."""

    def allow_request(self, request, view):
        if is_loadtest_request(request):
            return True
        return super().allow_request(request, view)


def get_client_ip(request) -> str:
    """Best-effort real client IP behind Cloudflare → host nginx → frontend nginx.

    Cloudflare overwrites ``CF-Connecting-IP`` with the true client address, so it
    is trusted first (the deployment is Cloudflare-fronted). Fall back to the first
    ``X-Forwarded-For`` hop, then ``X-Real-IP``, then ``REMOTE_ADDR``.
    """
    cf_ip = request.META.get('HTTP_CF_CONNECTING_IP')
    if cf_ip:
        return cf_ip.strip()

    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        first = xff.split(',')[0].strip()
        if first:
            return first

    real_ip = request.META.get('HTTP_X_REAL_IP')
    if real_ip:
        return real_ip.strip()

    return request.META.get('REMOTE_ADDR', '')


class ClientIPTrackingMixin:
    """Key rate limits on the real client IP, not the proxy container IP.

    Without this, DRF's default ident is ``REMOTE_ADDR`` (the frontend nginx
    container), so every anonymous visitor shares one bucket and the site trips
    its own ``anon`` limit. See ``get_client_ip`` for the resolution order.
    """

    def get_ident(self, request):
        return get_client_ip(request)


class LoadtestAnonRateThrottle(ClientIPTrackingMixin, LoadtestBypassMixin, AnonRateThrottle):
    pass


class LoadtestUserRateThrottle(ClientIPTrackingMixin, LoadtestBypassMixin, UserRateThrottle):
    pass
