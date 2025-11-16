"""
Tests for Content Security Policy configuration
"""
import os
from django.test import TestCase, override_settings
from importlib import reload
from config.addon import csp


class CSPConfigurationTests(TestCase):
    """Test CSP configuration for development vs production."""

    def test_production_csp_is_strict(self):
        """Verify production CSP has no unsafe-inline or unsafe-eval."""
        # Temporarily set production mode
        original_debug = os.environ.get("DJANGO_DEBUG")
        try:
            os.environ["DJANGO_DEBUG"] = "false"
            reload(csp)
            
            # Production should NOT have unsafe-inline or unsafe-eval
            self.assertNotIn("'unsafe-inline'", csp.CSP_SCRIPT_SRC)
            self.assertNotIn("'unsafe-eval'", csp.CSP_SCRIPT_SRC)
            self.assertNotIn("'unsafe-inline'", csp.CSP_STYLE_SRC)
            
            # Production should have nonce support
            self.assertIn("script-src", csp.CSP_INCLUDE_NONCE_IN)
            self.assertIn("style-src", csp.CSP_INCLUDE_NONCE_IN)
            
            # Production should NOT have WebSocket wildcards
            self.assertNotIn("ws:", csp.CSP_CONNECT_SRC)
            self.assertNotIn("wss:", csp.CSP_CONNECT_SRC)
            
        finally:
            # Restore original state
            if original_debug is not None:
                os.environ["DJANGO_DEBUG"] = original_debug
            else:
                os.environ.pop("DJANGO_DEBUG", None)
            reload(csp)

    def test_development_csp_is_relaxed(self):
        """Verify development CSP allows unsafe directives for admin."""
        # Temporarily set development mode
        original_debug = os.environ.get("DJANGO_DEBUG")
        try:
            os.environ["DJANGO_DEBUG"] = "true"
            reload(csp)
            
            # Development SHOULD have unsafe-inline and unsafe-eval
            self.assertIn("'unsafe-inline'", csp.CSP_SCRIPT_SRC)
            self.assertIn("'unsafe-eval'", csp.CSP_SCRIPT_SRC)
            self.assertIn("'unsafe-inline'", csp.CSP_STYLE_SRC)
            
            # Development SHOULD have WebSocket support
            self.assertIn("ws:", csp.CSP_CONNECT_SRC)
            self.assertIn("wss:", csp.CSP_CONNECT_SRC)
            
        finally:
            # Restore original state
            if original_debug is not None:
                os.environ["DJANGO_DEBUG"] = original_debug
            else:
                os.environ.pop("DJANGO_DEBUG", None)
            reload(csp)

    def test_production_has_frame_ancestors_none(self):
        """Verify frame-ancestors is set to 'none' in production."""
        original_debug = os.environ.get("DJANGO_DEBUG")
        try:
            os.environ["DJANGO_DEBUG"] = "false"
            reload(csp)
            
            self.assertEqual(csp.CSP_FRAME_ANCESTORS, ("'none'",))
            
        finally:
            if original_debug is not None:
                os.environ["DJANGO_DEBUG"] = original_debug
            else:
                os.environ.pop("DJANGO_DEBUG", None)
            reload(csp)

    def test_production_has_object_src_none(self):
        """Verify object-src is set to 'none' in production."""
        original_debug = os.environ.get("DJANGO_DEBUG")
        try:
            os.environ["DJANGO_DEBUG"] = "false"
            reload(csp)
            
            self.assertEqual(csp.CSP_OBJECT_SRC, ("'none'",))
            
        finally:
            if original_debug is not None:
                os.environ["DJANGO_DEBUG"] = original_debug
            else:
                os.environ.pop("DJANGO_DEBUG", None)
            reload(csp)
