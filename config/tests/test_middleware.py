"""
Tests for security middleware.
Tests CSP policies, security headers, and cookie security.
"""

import pytest
from unittest.mock import Mock
from django.http import HttpResponse
from django.test import RequestFactory

from config.middleware.security import (
    SecurityHeadersMiddleware,
    CookieSecurityMiddleware,
)
from config.middleware.csp_custom import CustomCSPMiddleware


class TestSecurityHeadersMiddleware:
    """Test SecurityHeadersMiddleware enforces security headers."""

    def setup_method(self):
        """Set up test data."""
        self.factory = RequestFactory()

        def get_response(request):
            response = HttpResponse("OK")
            response["Server"] = "Apache/2.4.1"  # Simulating server header
            return response

        self.middleware = SecurityHeadersMiddleware(get_response)

    def test_removes_server_header(self):
        """Test Server header is removed to hide version info."""
        request = self.factory.get("/")
        response = self.middleware(request)

        assert "Server" not in response

    def test_adds_x_content_type_options(self):
        """Test X-Content-Type-Options header is set to nosniff."""
        request = self.factory.get("/")
        response = self.middleware(request)

        assert response["X-Content-Type-Options"] == "nosniff"

    def test_adds_referrer_policy(self):
        """Test Referrer-Policy header is set correctly."""
        request = self.factory.get("/")
        response = self.middleware(request)

        assert response["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_adds_permissions_policy(self):
        """Test Permissions-Policy header restricts features."""
        request = self.factory.get("/")
        response = self.middleware(request)

        assert "Permissions-Policy" in response

        policy = response["Permissions-Policy"]
        assert "geolocation=()" in policy
        assert "microphone=()" in policy
        assert "camera=()" in policy
        assert "payment=()" in policy
        assert "usb=()" in policy

    def test_all_security_headers_present(self):
        """Test all security headers are present in response."""
        request = self.factory.get("/")
        response = self.middleware(request)

        # Verify all expected security headers
        assert "X-Content-Type-Options" in response
        assert "Referrer-Policy" in response
        assert "Permissions-Policy" in response
        assert "Server" not in response


class TestCookieSecurityMiddleware:
    """Test CookieSecurityMiddleware enforces secure cookie attributes."""

    def setup_method(self):
        """Set up test data."""
        self.factory = RequestFactory()

        def get_response(request):
            response = HttpResponse("OK")
            response.set_cookie("sessionid", "test-session-value")
            response.set_cookie("csrftoken", "test-csrf-value")
            response.set_cookie("custom", "custom-value")
            return response

        self.middleware = CookieSecurityMiddleware(get_response)

    def test_sessionid_cookie_httponly(self):
        """Test sessionid cookie has HttpOnly flag."""
        request = self.factory.get("/")
        response = self.middleware(request)

        sessionid_cookie = response.cookies.get("sessionid")
        assert sessionid_cookie is not None
        assert sessionid_cookie["httponly"] is True

    def test_csrftoken_cookie_httponly(self):
        """Test csrftoken cookie has HttpOnly flag."""
        request = self.factory.get("/")
        response = self.middleware(request)

        csrf_cookie = response.cookies.get("csrftoken")
        assert csrf_cookie is not None
        assert csrf_cookie["httponly"] is True

    def test_sessionid_cookie_samesite_strict(self):
        """Test sessionid cookie has SameSite=Strict."""
        request = self.factory.get("/")
        response = self.middleware(request)

        sessionid_cookie = response.cookies.get("sessionid")
        assert sessionid_cookie["samesite"] == "Strict"

    def test_csrftoken_cookie_samesite_strict(self):
        """Test csrftoken cookie has SameSite=Strict."""
        request = self.factory.get("/")
        response = self.middleware(request)

        csrf_cookie = response.cookies.get("csrftoken")
        assert csrf_cookie["samesite"] == "Strict"

    def test_custom_cookie_gets_samesite(self):
        """Test custom cookies get SameSite attribute."""
        request = self.factory.get("/")
        response = self.middleware(request)

        custom_cookie = response.cookies.get("custom")
        assert custom_cookie["samesite"] == "Strict"

    def test_no_cookies_response_handled(self):
        """Test middleware handles responses without cookies."""

        def get_response_no_cookies(request):
            return HttpResponse("OK")

        middleware = CookieSecurityMiddleware(get_response_no_cookies)
        request = self.factory.get("/")

        # Should not raise exception
        response = middleware(request)
        assert response.status_code == 200


class TestCustomCSPMiddleware:
    """Test CustomCSPMiddleware applies route-specific CSP policies."""

    def setup_method(self):
        """Set up test data."""
        self.factory = RequestFactory()

        def get_response(request):
            return HttpResponse("OK")

        self.middleware = CustomCSPMiddleware(get_response)

    def test_api_route_strict_csp(self):
        """Test API routes get strict CSP without unsafe-inline/unsafe-eval."""
        request = self.factory.get("/api/v1/users/")
        response = self.middleware(request)

        csp = response["Content-Security-Policy"]

        # API routes should NOT allow unsafe-inline or unsafe-eval
        assert "'unsafe-inline'" not in csp
        assert "'unsafe-eval'" not in csp

        # Should have strict policies
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "style-src 'self'" in csp

    def test_admin_route_relaxed_csp(self):
        """Test admin routes get relaxed CSP for Unfold compatibility."""
        request = self.factory.get("/admin/users/user/")
        response = self.middleware(request)

        csp = response["Content-Security-Policy"]

        # Admin routes SHOULD allow unsafe-inline/unsafe-eval for Unfold
        assert "'unsafe-inline'" in csp
        assert "'unsafe-eval'" in csp

        # Should allow Google Fonts for Unfold
        assert "https://fonts.googleapis.com" in csp
        assert "https://fonts.gstatic.com" in csp

    def test_csp_frame_ancestors_none(self):
        """Test frame-ancestors is set to none (clickjacking protection)."""
        request = self.factory.get("/api/v1/users/")
        response = self.middleware(request)

        csp = response["Content-Security-Policy"]
        assert "frame-ancestors 'none'" in csp

    def test_csp_base_uri_self(self):
        """Test base-uri is restricted to self."""
        request = self.factory.get("/api/v1/users/")
        response = self.middleware(request)

        csp = response["Content-Security-Policy"]
        assert "base-uri 'self'" in csp

    def test_csp_form_action_self(self):
        """Test form-action is restricted to self."""
        request = self.factory.get("/api/v1/users/")
        response = self.middleware(request)

        csp = response["Content-Security-Policy"]
        assert "form-action 'self'" in csp

    def test_csp_object_src_none(self):
        """Test object-src is set to none (Flash/Java protection)."""
        request = self.factory.get("/api/v1/users/")
        response = self.middleware(request)

        csp = response["Content-Security-Policy"]
        assert "object-src 'none'" in csp

    def test_csp_img_src_allows_data(self):
        """Test img-src allows data: URIs for inline images."""
        request = self.factory.get("/api/v1/users/")
        response = self.middleware(request)

        csp = response["Content-Security-Policy"]
        assert "img-src 'self' data:" in csp

    def test_x_content_type_options_set(self):
        """Test X-Content-Type-Options is set by CSP middleware."""
        request = self.factory.get("/api/v1/users/")
        response = self.middleware(request)

        assert response["X-Content-Type-Options"] == "nosniff"

    def test_public_route_strict_csp(self):
        """Test non-admin/non-API routes also get strict CSP."""
        request = self.factory.get("/health/")
        response = self.middleware(request)

        csp = response["Content-Security-Policy"]

        # Public routes should also be strict
        assert "'unsafe-inline'" not in csp
        assert "'unsafe-eval'" not in csp

    def test_csp_connect_src_includes_ws_in_debug(self):
        """Test connect-src includes WebSocket in debug mode."""
        # Set debug mode
        self.middleware.is_debug = True

        request = self.factory.get("/api/v1/users/")
        response = self.middleware(request)

        csp = response["Content-Security-Policy"]

        # Should allow WebSocket connections in debug mode
        assert "ws:" in csp
        assert "wss:" in csp

    def test_csp_connect_src_no_ws_in_production(self):
        """Test connect-src excludes WebSocket in production."""
        # Set production mode
        self.middleware.is_debug = False

        request = self.factory.get("/api/v1/users/")
        response = self.middleware(request)

        csp = response["Content-Security-Policy"]

        # Should NOT allow WebSocket in production by default
        # (connect-src should be just 'self')
        connect_src_part = [part for part in csp.split(";") if "connect-src" in part][0]
        assert connect_src_part.strip() == "connect-src 'self'"

    def test_admin_route_detection(self):
        """Test admin route detection is accurate."""
        # Admin routes
        admin_paths = [
            "/admin/",
            "/admin/users/",
            "/admin/users/user/",
            "/admin/auth/group/add/",
        ]

        for path in admin_paths:
            request = self.factory.get(path)
            response = self.middleware(request)
            csp = response["Content-Security-Policy"]

            # All admin paths should have relaxed CSP
            assert "'unsafe-inline'" in csp, f"Failed for {path}"

    def test_non_admin_route_detection(self):
        """Test non-admin routes are detected correctly."""
        # Non-admin routes
        non_admin_paths = [
            "/api/v1/users/",
            "/api/v1/auth/login/",
            "/health/",
            "/admin-panel/",  # Similar name but not /admin/
        ]

        for path in non_admin_paths:
            request = self.factory.get(path)
            response = self.middleware(request)
            csp = response["Content-Security-Policy"]

            # All non-admin paths should have strict CSP
            assert "'unsafe-inline'" not in csp, f"Failed for {path}"
            assert "'unsafe-eval'" not in csp, f"Failed for {path}"


class TestMiddlewareIntegration:
    """Test multiple middleware working together."""

    def test_all_middleware_chain(self):
        """Test all security middleware can be chained together."""
        factory = RequestFactory()

        def base_response(request):
            response = HttpResponse("OK")
            response["Server"] = "Apache"
            response.set_cookie("sessionid", "test-value")
            return response

        # Chain middleware
        middleware1 = SecurityHeadersMiddleware(base_response)
        middleware2 = CookieSecurityMiddleware(middleware1)
        middleware3 = CustomCSPMiddleware(middleware2)

        request = factory.get("/api/v1/test/")
        response = middleware3(request)

        # Verify all middleware effects are present
        # From SecurityHeadersMiddleware
        assert "Server" not in response
        assert response["Referrer-Policy"] == "strict-origin-when-cross-origin"

        # From CookieSecurityMiddleware
        sessionid = response.cookies.get("sessionid")
        assert sessionid["httponly"] is True
        assert sessionid["samesite"] == "Strict"

        # From CustomCSPMiddleware
        assert "Content-Security-Policy" in response
        assert response["X-Content-Type-Options"] == "nosniff"
