"""
Tests for WhiteNoise security headers utility.
"""

from django.test import TestCase
from config.utils.whitenoise_headers import add_security_headers


class TestAddSecurityHeaders(TestCase):
    """Test add_security_headers function."""

    def test_adds_x_content_type_options(self):
        """Adds X-Content-Type-Options: nosniff."""
        headers = {}
        result = add_security_headers(headers, "/path/to/file.js", "/static/js/file.js")

        self.assertEqual(result["X-Content-Type-Options"], "nosniff")

    def test_adds_cache_control_for_static_files(self):
        """Adds Cache-Control header for static files."""
        headers = {}
        result = add_security_headers(
            headers, "/path/to/file.css", "/static/css/file.css"
        )

        self.assertIn("Cache-Control", result)
        self.assertIn("max-age=31536000", result["Cache-Control"])
        self.assertIn("immutable", result["Cache-Control"])

    def test_cache_control_for_non_static_paths(self):
        """Cache-Control only for /static/ paths."""
        headers = {}
        result = add_security_headers(
            headers, "/path/to/file.js", "/media/uploads/file.js"
        )

        # Should still have X-Content-Type-Options but not Cache-Control
        self.assertIn("X-Content-Type-Options", result)

    def test_modifies_existing_headers_dict(self):
        """Modifies and returns the provided headers dict."""
        headers = {"Content-Type": "text/css"}
        result = add_security_headers(
            headers, "/path/to/style.css", "/static/css/style.css"
        )

        self.assertEqual(result["Content-Type"], "text/css")
        self.assertEqual(result["X-Content-Type-Options"], "nosniff")
        self.assertIs(result, headers)  # Same dict object

    def test_works_with_various_file_types(self):
        """Works with different static file types."""
        file_types = [
            ("/static/js/app.js", "/path/to/app.js"),
            ("/static/css/style.css", "/path/to/style.css"),
            ("/static/img/logo.png", "/path/to/logo.png"),
            ("/static/fonts/font.woff2", "/path/to/font.woff2"),
        ]

        for url, path in file_types:
            headers = {}
            result = add_security_headers(headers, path, url)
            self.assertEqual(result["X-Content-Type-Options"], "nosniff")
            self.assertIn("Cache-Control", result)
