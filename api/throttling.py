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


class LoadtestAnonRateThrottle(LoadtestBypassMixin, AnonRateThrottle):
    pass


class LoadtestUserRateThrottle(LoadtestBypassMixin, UserRateThrottle):
    pass
