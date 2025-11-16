# config/tests/test_security_headers.py

from django.test import TestCase, Client
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings


def get_user_model_lazy():
    from django.contrib.auth import get_user_model

    return get_user_model()


User = get_user_model_lazy()


class SecurityHeadersTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_security_headers_on_admin(self):
        response = self.client.get("/admin/login/")

        self.assertEqual(response.status_code, 200)

        # Core headers
        self.assertIn("Content-Security-Policy", response.headers)
        self.assertEqual(
            response.headers.get("X-Content-Type-Options"),
            "nosniff",
        )
        self.assertEqual(
            response.headers.get("Referrer-Policy"),
            "strict-origin-when-cross-origin",
        )

        # Try to ensure we’re not leaking framework/server
        self.assertNotIn("Server", response.headers)

    def test_csrf_cookie_flags(self):
        response = self.client.get("/admin/login/")

        csrf_cookie = response.cookies.get("csrftoken")
        self.assertIsNotNone(csrf_cookie, "csrftoken cookie should be set")

        # HttpOnly should always be true
        self.assertTrue(
            csrf_cookie["httponly"],
            "CSRF cookie must be HttpOnly",
        )

        # Only assert 'secure' if you’ve enabled it in settings
        if settings.CSRF_COOKIE_SECURE:
            self.assertTrue(
                csrf_cookie["secure"],
                "CSRF cookie must be Secure when CSRF_COOKIE_SECURE=True",
            )


class SecurityHSTSTests(TestCase):
    @override_settings(SECURE_HSTS_SECONDS=3600, SECURE_SSL_REDIRECT=True)
    def test_hsts_header_present_for_https(self):
        # secure=True simulates HTTPS request
        response = self.client.get("/admin/login/", secure=True)

        self.assertIn("Strict-Transport-Security", response.headers)
        hsts = response.headers["Strict-Transport-Security"]
        self.assertIn("max-age=3600", hsts)


class LoginLockoutTests(TestCase):
    def setUp(self):
        # Using the same email/password as your real superuser,
        # but this is created in the *test* DB, not your real one.
        self.email = "tawanda@kinwise.co.nz"
        self.password = "YIANDTrazzy101%%"

        # Make this user an admin so they can actually log into /admin/
        self.user = User.objects.create_superuser(
            email=self.email,
            password=self.password,
        )

        # Whatever your USERNAME_FIELD is (very likely "email")
        self.login_identifier = getattr(self.user, User.USERNAME_FIELD)

    def test_user_is_locked_out_after_failures(self):
        login_url = "/admin/login/"

        # How many failures before lockout? default 5, or your setting.
        failure_limit = getattr(settings, "AXES_FAILURE_LIMIT", 5)

        # Axes + Django admin expect the POST field name to be "username",
        # but the value is whatever USERNAME_FIELD is (email here).
        for _ in range(failure_limit):
            self.client.post(
                login_url,
                {
                    "username": self.login_identifier,
                    "password": "wrongpass",
                },
            )

        # Now try with the *correct* password – should be locked out
        resp = self.client.post(
            login_url,
            {
                "username": self.login_identifier,
                "password": self.password,
            },
        )

        # Successful admin login → 302 redirect; anything else means "no login".
        self.assertNotEqual(
            resp.status_code,
            302,
            "Locked out user should not be able to log in",
        )
