"""
Tests for security middleware.
"""

import pytest
from django.test import TestCase, RequestFactory
from django.http import HttpResponse
from config.middleware.security import (
    SecurityHeadersMiddleware,
    CookieSecurityMiddleware,
)


class TestSecurityHeadersMiddleware(TestCase):
    """Test security headers middleware."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()

    def get_response_with_server(self, request):
        """Response with Server header."""
        response = HttpResponse("OK")
        response["Server"] = "TestServer/1.0"
        return response

    def get_response_plain(self, request):
        """Plain response."""
        return HttpResponse("OK")

    def test_removes_server_header(self):
        """Server header is removed."""
        middleware = SecurityHeadersMiddleware(self.get_response_with_server)
        request = self.factory.get("/")
        response = middleware(request)

        self.assertNotIn("Server", response)

    def test_adds_x_content_type_options(self):
        """X-Content-Type-Options header is added."""
        middleware = SecurityHeadersMiddleware(self.get_response_plain)
        request = self.factory.get("/")
        response = middleware(request)

        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_adds_referrer_policy(self):
        """Referrer-Policy header is added."""
        middleware = SecurityHeadersMiddleware(self.get_response_plain)
        request = self.factory.get("/")
        response = middleware(request)

        self.assertEqual(response["Referrer-Policy"], "strict-origin-when-cross-origin")

    def test_adds_permissions_policy(self):
        """Permissions-Policy header is added."""
        middleware = SecurityHeadersMiddleware(self.get_response_plain)
        request = self.factory.get("/")
        response = middleware(request)

        self.assertIn("geolocation=()", response["Permissions-Policy"])
        self.assertIn("microphone=()", response["Permissions-Policy"])


class TestCookieSecurityMiddleware(TestCase):
    """Test cookie security middleware."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()

    def get_response_with_cookies(self, request):
        """Response with cookies."""
        response = HttpResponse("OK")
        response.set_cookie("sessionid", "abc123")
        response.set_cookie("csrftoken", "xyz789")
        response.set_cookie("other", "value")
        return response

    def get_response_plain(self, request):
        """Response without cookies."""
        return HttpResponse("OK")

    def test_sets_httponly_on_sessionid(self):
        """sessionid cookie gets HttpOnly."""
        middleware = CookieSecurityMiddleware(self.get_response_with_cookies)
        request = self.factory.get("/")
        response = middleware(request)

        # HttpOnly should be set (value is True, not '')
        self.assertIn("httponly", response.cookies["sessionid"])
        self.assertEqual(response.cookies["sessionid"]["httponly"], True)

    def test_sets_httponly_on_csrftoken(self):
        """csrftoken cookie gets HttpOnly."""
        middleware = CookieSecurityMiddleware(self.get_response_with_cookies)
        request = self.factory.get("/")
        response = middleware(request)

        # HttpOnly should be set (value is True, not '')
        self.assertIn("httponly", response.cookies["csrftoken"])
        self.assertEqual(response.cookies["csrftoken"]["httponly"], True)

    def test_sets_samesite_on_all_cookies(self):
        """SameSite=Strict on all cookies."""
        middleware = CookieSecurityMiddleware(self.get_response_with_cookies)
        request = self.factory.get("/")
        response = middleware(request)

        for cookie_name in ["sessionid", "csrftoken", "other"]:
            self.assertIn("samesite", response.cookies[cookie_name])
            # Should have samesite set
            self.assertTrue(response.cookies[cookie_name]["samesite"])

    def test_no_cookies_no_error(self):
        """No error when response has no cookies."""
        middleware = CookieSecurityMiddleware(self.get_response_plain)
        request = self.factory.get("/")
        response = middleware(request)

        self.assertEqual(response.status_code, 200)

    def test_preserves_existing_samesite(self):
        """Doesn't override existing SameSite."""

        def get_response_with_samesite(request):
            response = HttpResponse("OK")
            response.set_cookie("sessionid", "abc123", samesite="Lax")
            return response

        middleware = CookieSecurityMiddleware(get_response_with_samesite)
        request = self.factory.get("/")
        response = middleware(request)

        # Should preserve Lax
        self.assertEqual(response.cookies["sessionid"]["samesite"], "Lax")
