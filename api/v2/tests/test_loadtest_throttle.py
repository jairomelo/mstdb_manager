"""Tests for the LOADTEST_TOKEN-gated throttle bypass.

The bypass must be inert by default, must not weaken authentication or
permissions, and must only skip rate limiting for requests carrying the
configured ``X-Loadtest-Token`` header.
"""

from contextlib import contextmanager

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.test import APITestCase

from api.throttling import (
    LOADTEST_TOKEN_HEADER,
    LoadtestAnonRateThrottle,
    LoadtestUserRateThrottle,
    is_loadtest_request,
)

HEALTH_URL = '/api/v2/health/'
WHOAMI_URL = '/api/v2/whoami/'

LOCMEM_CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'loadtest-throttle-tests',
    }
}

TOKEN_HEADER_META = {
    'X-Loadtest-Token': 'HTTP_X_LOADTEST_TOKEN',
}[LOADTEST_TOKEN_HEADER]


class _FakeRequest:
    def __init__(self, token=None, remote_addr='203.0.113.9'):
        self.META = {'REMOTE_ADDR': remote_addr}
        if token is not None:
            self.META[TOKEN_HEADER_META] = token
        self.user = AnonymousUser()


@contextmanager
def _patched_rates(rates):
    """Temporarily override the throttle rate map used by SimpleRateThrottle."""
    original = SimpleRateThrottle.THROTTLE_RATES
    SimpleRateThrottle.THROTTLE_RATES = rates
    try:
        yield
    finally:
        SimpleRateThrottle.THROTTLE_RATES = original


class IsLoadtestRequestTests(TestCase):
    def test_false_when_token_unset(self):
        with override_settings(LOADTEST_TOKEN=''):
            self.assertFalse(is_loadtest_request(_FakeRequest(token='anything')))

    def test_false_when_header_absent(self):
        with override_settings(LOADTEST_TOKEN='secret'):
            self.assertFalse(is_loadtest_request(_FakeRequest()))

    def test_false_when_header_mismatched(self):
        with override_settings(LOADTEST_TOKEN='secret'):
            self.assertFalse(is_loadtest_request(_FakeRequest(token='wrong')))

    def test_true_when_header_matches(self):
        with override_settings(LOADTEST_TOKEN='secret'):
            self.assertTrue(is_loadtest_request(_FakeRequest(token='secret')))


@override_settings(CACHES=LOCMEM_CACHES)
class ThrottleClassTests(TestCase):
    def setUp(self):
        cache.clear()

    def _anon_throttle(self):
        throttle = LoadtestAnonRateThrottle()
        throttle.rate = '2/minute'
        throttle.num_requests, throttle.duration = throttle.parse_rate(throttle.rate)
        return throttle

    def test_bypass_inert_when_token_unset(self):
        with override_settings(LOADTEST_TOKEN=''):
            throttle = self._anon_throttle()
            request = _FakeRequest(token='secret')
            self.assertTrue(throttle.allow_request(request, None))
            self.assertTrue(throttle.allow_request(request, None))
            self.assertFalse(throttle.allow_request(request, None))

    def test_invalid_token_does_not_bypass(self):
        with override_settings(LOADTEST_TOKEN='secret'):
            throttle = self._anon_throttle()
            request = _FakeRequest(token='wrong')
            self.assertTrue(throttle.allow_request(request, None))
            self.assertTrue(throttle.allow_request(request, None))
            self.assertFalse(throttle.allow_request(request, None))

    def test_valid_token_bypasses_rate_limit(self):
        with override_settings(LOADTEST_TOKEN='secret'):
            throttle = self._anon_throttle()
            request = _FakeRequest(token='secret')
            for _ in range(25):
                self.assertTrue(throttle.allow_request(request, None))

    def test_user_throttle_inherits_bypass(self):
        with override_settings(LOADTEST_TOKEN='secret'):
            self.assertTrue(issubclass(LoadtestUserRateThrottle, SimpleRateThrottle))


@override_settings(CACHES=LOCMEM_CACHES)
class ThrottleBypassIntegrationTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_default_throttles_are_loadtest_aware(self):
        from rest_framework.settings import api_settings

        names = [
            getattr(cls, '__name__', cls)
            for cls in api_settings.DEFAULT_THROTTLE_CLASSES
        ]
        self.assertIn('LoadtestAnonRateThrottle', names)
        self.assertIn('LoadtestUserRateThrottle', names)

    def test_header_bypasses_exhausted_limit(self):
        with _patched_rates({'anon': '1/minute', 'user': '1/minute'}):
            with override_settings(LOADTEST_TOKEN='secret'):
                self.assertEqual(self.client.get(HEALTH_URL).status_code, 200)
                self.assertEqual(self.client.get(HEALTH_URL).status_code, 429)
                for _ in range(5):
                    bypass = self.client.get(
                        HEALTH_URL, HTTP_X_LOADTEST_TOKEN='secret')
                    self.assertEqual(bypass.status_code, 200)

    def test_wrong_token_still_throttled(self):
        with _patched_rates({'anon': '1/minute', 'user': '1/minute'}):
            with override_settings(LOADTEST_TOKEN='secret'):
                self.assertEqual(self.client.get(HEALTH_URL).status_code, 200)
                throttled = self.client.get(
                    HEALTH_URL, HTTP_X_LOADTEST_TOKEN='wrong')
                self.assertEqual(throttled.status_code, 429)

    def test_bypass_does_not_grant_authentication(self):
        with override_settings(LOADTEST_TOKEN='secret'):
            response = self.client.get(
                WHOAMI_URL, HTTP_X_LOADTEST_TOKEN='secret')
        self.assertIn(response.status_code, (401, 403))

    def test_bypass_inert_for_normal_clients(self):
        with _patched_rates({'anon': '1/minute', 'user': '1/minute'}):
            with override_settings(LOADTEST_TOKEN='secret'):
                self.assertEqual(self.client.get(HEALTH_URL).status_code, 200)
                # No header at all -> normal throttling still applies.
                self.assertEqual(self.client.get(HEALTH_URL).status_code, 429)
