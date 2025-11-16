
# Django Coding Best Practices

This guide consolidates Django official documentation and the HackSoftware Django Styleguide to provide actionable best practices for building maintainable, secure, and scalable Django applications.

---

## 1. Project Structure
- Use a clear modular structure: `apps/` for domain apps, `config/` for settings and middleware.
- Follow Django's recommended layout: `manage.py` at root, settings split into `base.py`, `local.py`, `production.py`.
- Keep reusable logic in `common/` or `core/` apps.

References:
- [Django Project Structure](https://docs.djangoproject.com/en/stable/intro/tutorial01/)
- [HackSoftware Styleguide](https://github.com/HackSoftware/Django-Styleguide)

---

## 2. Models
- Use `verbose_name` and `help_text` for better admin readability.
- Add `validators` from `django.core.validators` for field-level validation.
- Define `ordering` and `permissions` in `Meta`.
- Use `__str__` for meaningful string representation.
- Avoid business logic in models; use service layer.

References:
- [Models](https://docs.djangoproject.com/en/stable/topics/db/models/)
- [Meta Options](https://docs.djangoproject.com/en/stable/ref/models/options/)

---

## 3. Serializers
- Use `ModelSerializer` for DRY code.
- Define `read_only_fields` in `Meta` instead of manual flags.
- Implement custom validation with `validate_<field>` methods.
- Keep serializers thin; heavy logic goes to services.

References:
- [DRF Serializers](https://www.django-rest-framework.org/api-guide/serializers/)

---

## 4. Views
- Prefer `ViewSet` + DRF routers for CRUD endpoints.
- Use generic mixins (`ListModelMixin`, `CreateModelMixin`) for common patterns.
- Apply throttling via `throttle_classes` at class level.
- Keep views thin; delegate business logic to services.

References:
- [Class-Based Views](https://docs.djangoproject.com/en/stable/topics/class-based-views/)
- [DRF ViewSets](https://www.django-rest-framework.org/api-guide/viewsets/)

---

## 5. URLs
- Use DRF routers for ViewSets.
- Follow RESTful naming conventions.
- Group related endpoints under logical namespaces.

References:
- [URL Dispatcher](https://docs.djangoproject.com/en/stable/topics/http/urls/)

---

## 6. Middleware
- Position security middleware correctly: `SecurityMiddleware` first, CSP after.
- Add custom middleware for headers (X-Content-Type-Options, Referrer-Policy).

References:
- [Middleware](https://docs.djangoproject.com/en/stable/topics/http/middleware/)

---

## 7. Security
- Enable `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS='DENY'`, HSTS in production.
- Use `CSRF_COOKIE_HTTPONLY=True` and `SESSION_COOKIE_HTTPONLY=True`.
- Implement CSP via `django-csp` or custom middleware.
- Remove `Server` header to prevent version leakage.

References:
- [Security](https://docs.djangoproject.com/en/stable/topics/security/)

---

## 8. Testing
- Use `django.test.TestCase` for database tests.
- Use `reverse()` for URL resolution.
- Add fixtures for reusable test data.
- Include performance tests for async tasks.

References:
- [Testing](https://docs.djangoproject.com/en/stable/topics/testing/)

---

## 9. Admin
- Customize admin with `list_display`, `search_fields`, and `ordering`.
- Use `readonly_fields` for immutable data.

References:
- [Admin Site](https://docs.djangoproject.com/en/stable/ref/contrib/admin/)

---

## 10. HackSoftware Styleguide Highlights
- Use service layer for business logic.
- Keep views and serializers thin.
- Avoid fat models; prefer explicit service functions.
- Use explicit imports, avoid wildcard imports.
- Apply consistent naming conventions for apps, models, and files.

References:
- [HackSoftware Django Styleguide](https://github.com/HackSoftware/Django-Styleguide)

---

This guide ensures your Django codebase is maintainable, secure, and aligned with industry standards.
