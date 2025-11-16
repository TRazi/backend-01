# KinWise Backend — Developer Guide

**Version**: 2.8  
**Last Updated**: November 2025  
**Status**: Production-Ready (97.25% Test Coverage Achieved)

This document provides an in-depth, repo-accurate guide for the KinWise backend. It covers architecture, configuration, domain models, security posture, operations, and development workflows.


Table of Contents
1. Overview
2. Architecture
3. Technology Stack
4. Project Structure
5. Settings & Environments
6. Security & Compliance
7. Applications & Domain Models
8. Admin Interface
9. Development Guide
10. Testing & Quality
11. Migrations & Data
12. Troubleshooting
13. Roadmap

---

## Overview

 KinWise is a production-ready Django-based backend for multi-household family finance management. Built as a multi-tenant SaaS application with 17 domain apps, it provides comprehensive financial tracking, budgeting, goal management, and educational content with enterprise-grade security controls. 

 Also bare in mind that when writing any import statements that I have this line in my base.py: 

 # Add apps to Python path
sys.path.insert(0, os.path.join(BASE_DIR, "apps"))



**Current Status**: ✅ Production-Ready (v2.7)
- **Test Coverage**: 97.25% (837 tests passing, 15 skipped, 0 failures)
- **Quality**: All model validation, business logic, and security controls fully tested
- **Code Quality**: SonarQube integration with Docker for continuous code analysis
- **Security**: SOC 2-aligned controls + Route-based CSP + CORS + CSRF enforcement + ZAP validated (0 HIGH vulnerabilities)
- **Uncovered Lines**: 293 (down from 666, -56% reduction)
- **Files with 100% Coverage**: 211
- **API**: Full REST API with JWT authentication + CORS protection
- **Audit**: Comprehensive audit logging system
- **Rate Limiting**: Multi-layer throttling protection
- **CORS**: Production-ready Cross-Origin Resource Sharing for frontend integration
- **CSP**: Route-specific Content Security Policy (strict API, relaxed admin)
- **Static Security**: WhiteNoise with X-Content-Type-Options headers
- **CSRF Protection**: Enforced on all session endpoints (SessionPingView, admin_logout POST-only)

Key goals
- ✅ Clear domain separation by app under `apps/` (17 apps implemented)
- ✅ Custom user model with email login and locale/role fields
- ✅ Multi-tenant architecture with household-based data isolation
- ✅ Defensive defaults: CSP, HSTS, cookie flags, Axes lockout, JSON logging
- ✅ Modern Django Admin via Unfold with curated navigation
- ✅ Service layer pattern for business logic
- ✅ Comprehensive audit trail for compliance
- ✅ Rate limiting and account lockout protection

---

## Target Market & ICPs (Ideal Customer Profiles)

KinWise serves diverse household types across New Zealand with tailored features for each segment:

### Consumer Market (B2C)

**ICP1: Family Households**
- **Profile**: 2+ adults, 1-3 kids (ages 8-19), household income $60k-$120k
- **Location**: Urban/suburban NZ
- **Pain Points**: Living paycheck to paycheck, no spending visibility, kids' financial education gap
- **Motivation**: Peace of mind, teaching kids money skills, kids' future
- **Key Features**: Shared dashboards, kids' rewards/stickers, family goals, role-based access (parent, teen, child)

**ICP2: DINK Couples (Double Income, No Kids)**
- **Profile**: 2 adults, household income $100k-$200k combined
- **Location**: Urban centres
- **Pain Points**: "Yours, mine, ours" confusion, lifestyle creep, different spending philosophies, unequal incomes (70/30 split)
- **Motivation**: Travel, investments, early retirement, aligned financial goals
- **Key Features**: Proportional expense splitting, investment tracking, joint goal setting, bill automation

**ICP3: SINK Couples (Single Income, No Kids)**
- **Profile**: 2 adults, household income $50k-$100k single income
- **Location**: Anywhere in NZ
- **Pain Points**: Single income pressure, non-earner guilt, job loss fear, transition periods (maternity, study, redundancy)
- **Motivation**: Stability, emergency fund building, maximizing single income, strict budget discipline
- **Key Features**: Budget discipline tools, spending accountability, savings goals, category tracking

**ICP4: Student Flats**
- **Profile**: 3-5 flatmates, university students (Auckland, Wellington, Otago, Canterbury)
- **Pain Points**: Bill splitting chaos, StudyLink budgeting, tight budgets, irregular income, flat money drama
- **Motivation**: Avoid flat drama, stretch StudyLink allowance, learn budgeting basics
- **Key Features**: TransactionSplit for bill splitting, flatmate role permissions, simple tracking, mobile-first UX

**ICP5: Individuals (Solo Users)**
- **Profile**: Single person, ages 16-45, learning to budget or managing personal finances
- **Pain Points**: No financial education, want independence, tracking personal spending
- **Motivation**: Personal goals, financial independence, building good habits
- **Key Features**: Simple tracking, goal setting, lessons/education content, privacy controls

### Business Market (B2B - "Whānau Works")

**ICP6: Corporate/Organizations**
- **Profile**: Businesses, non-profits, schools, clubs, government departments
- **Organisation Types**: Corporate, non-profit, education, government, club
- **Use Cases**: Employee expense management, team budgets, department tracking, community group finances
- **Key Features**: Organisation model, member capacity management, org-level billing, multiple admins, financial year configuration
- **Subscription Tiers**: ww_starter (up to 50 members), ww_growth, ww_enterprise

### Pricing Alignment
- **B2C (Families/Couples/Students/Individuals)**: $5.99/month Plus tier
- **B2B (Organizations)**: $50-$500/month org tiers based on member count
- **Free Tier**: 1 household admin, manual entry, 30-day history, 2 accounts (acquisition/trial)

---

## Architecture

High-level
- Multi-app Django project with split settings (`config/settings/base.py`, `local.py`, `production.py`).
- `manage.py` defaults to `config.settings.local` for local development.
- Domain logic primarily expressed through models and enums; service layers can be added per app as needed (e.g., transactions, goals).
- Security middleware stack enforces SOC 2–inspired headers and policies.

 Request flow (current)
1. HTTP → Nginx/ASGI/WSGI (deployment-specific)
2. `django.middleware.security.SecurityMiddleware`
3. `whitenoise.middleware.WhiteNoiseMiddleware` (Static files with security headers)
4. `config.middleware.security.SecurityHeadersMiddleware` (X-Content-Type-Options, Referrer-Policy, Permissions-Policy)
5. `corsheaders.middleware.CorsMiddleware` (CORS headers - before CommonMiddleware)
6. `django.contrib.sessions.middleware.SessionMiddleware`
7. `django.middleware.common.CommonMiddleware`
8. `django.middleware.csrf.CsrfViewMiddleware`
9. `axes.middleware.AxesMiddleware` (Login attempt tracking)
10. `config.middleware.csp_custom.CustomCSPMiddleware` (Route-based Content-Security-Policy)
11. `django.contrib.auth.middleware.AuthenticationMiddleware`
12. `config.middleware.security.CookieSecurityMiddleware` (HttpOnly, SameSite enforcement)
13. `config.middleware.session.IdleTimeoutMiddleware` (Session timeout with grace period)
14. `django.contrib.messages.middleware.MessageMiddleware`
15. `django.middleware.clickjacking.XFrameOptionsMiddleware`
16. `django.middleware.locale.LocaleMiddleware`
17. `config.utils.ratelimit.AdminLoginRateLimitMiddleware` (Rate limiting for admin login)
18. Admin site routes and API v1 routes (see `config/api_v1_urls.py`)

---

## Technology Stack

- Django 5.2, Python 3.10+
- Django REST Framework 3.15.2 (fully integrated with JWT authentication)
- Auth/Security: `django-axes`, `django-csp`, `django-otp`, `pyotp`, `django-ratelimit`, `djangorestframework-simplejwt`, `django-cors-headers`
- Caching/Stores: `django-redis` (Redis), SQLite (local), Postgres via `dj-database-url` when `DATABASE_URL` is set
- Admin: `django-unfold` 0.69.0
- Static: `whitenoise` 6.11.0 (with security headers)
- Task Queue: `celery` 5.4.0 with `django-celery-beat` 2.8.1 and `django-celery-results` 2.6.0
- Cloud Services: `boto3` (AWS S3, Textract for OCR)
- Email: Django email with HTML templates
- Logging/Observability: `python-json-logger`, `sentry-sdk` (available)
- Health: `django-health-check` (available)
- Tooling: `black`, `flake8`, `mypy`, `pytest`, `pytest-django`, `safety` (security scanning)

See `requirements.txt` for exact versions.

---

## Project Structure

```
backend/
├── manage.py
├── apps/                     # All Django apps live here
│   ├── common/               # Shared base models
│   ├── users/                # Custom user model, roles/locales
│   ├── households/           # Household & memberships
│   ├── accounts/             # Financial accounts
│   ├── transactions/         # Transactions & tags
│   ├── categories/           # Category hierarchy
│   ├── budgets/              # Budgets & budget items
│   ├── goals/                # Goals & progress
│   ├── bills/                # Bills & reminders
│   ├── alerts/               # Alerting models
│   ├── organisations/        # Organisation linkage (present)
│   ├── rewards/              # Gamification rewards
│   └── lessons/              # Financial lessons (present)
├── config/
│   ├── settings/
│   │   ├── base.py           # Core settings (INSTALLED_APPS, middleware, security)
│   │   ├── local.py          # Local overrides (SQLite or DATABASE_URL)
│   │   ├── production.py     # Production overrides
│   │   └── security.py       # Security constants & CSP flags
│   ├── api_v1_urls.py        # Central API v1 router (auth, schema, per-app urls)
│   ├── addon/
│   │   ├── csp.py            # CSP directives (nonce, S3 allow-list)
│   │   └── logging.py        # JSON logging config
│   ├── middleware/
│   │   └── security.py       # Header hardening (nosniff, referrer)
│   ├── scripts/
│   │   └── unfold.py         # Unfold admin configuration
│   ├── tests/
│   │   └── test_security_headers.py
│   ├── env.py                # `BASE_DIR`, environ init
│   ├── urls.py               # Admin only (no API routes yet)
│   ├── asgi.py
│   └── wsgi.py
├── templates/
│   └── admin/                # Custom admin templates (base_ste.html, etc.)
├── static/                   # Static assets (admin overrides, unfold)
├── requirements.txt
├── .env.example              # Minimal environment template (local)
└── BACKEND_DOCUMENTATION.md  # This document
```

---

## Settings & Environments

Entry point
- `manage.py` sets `DJANGO_SETTINGS_MODULE=config.settings.local`.

Base (`config/settings/base.py`)
- Adds `apps/` to `PYTHONPATH` and loads `.env`.
- INSTALLED_APPS: `unfold`, `axes`, Django contrib apps, `rest_framework`, and all domain 
- Middleware: Security, CSP, Axes, Sessions, Common, CSRF, Auth, Messages, XFrameOptions, Locale.
- Auth: `AUTH_USER_MODEL = "users.User"`; Backends: Axes + Django model backend.
- Static: `STATIC_ROOT=staticfiles`, `STATICFILES_DIRS=[static]`.
- i18n: default `en`, `Pacific/Auckland` timezone, locale support.
- Imports: `config/settings/security.py`, `config/addon/logging.py`, `config/addon/csp.py`.

Local (`config/settings/local.py`)
- Uses `DATABASE_URL` if provided; otherwise SQLite at `db.sqlite3`.

Production (`config/settings/production.py`)
- `DEBUG=False`, `ALLOWED_HOSTS` from env; extend base for production runtime.

Environment variables (examples)
- `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `ALLOWED_HOSTS`
- `DATABASE_URL` (Postgres via `dj-database-url`)
- `REDIS_URL` (for cache/locks and throttling)
- `REDIS_URL_RATELIMIT` (optional, separate store for rate limiting)
- `DJANGO_LOG_LEVEL`
- `AWS_STORAGE_BUCKET_NAME` (CSP allow-list for S3 assets)
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` (Redis URLs for Celery)
- `FRONTEND_URL` (for email verification links, default: `http://localhost:3000`)
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` (for S3 and Textract OCR)
- `AWS_TEXTRACT_ENABLED` (enable receipt OCR, default: False)
- `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` (email configuration)

---

## Security & Compliance

Headers & transport
- `SECURE_CONTENT_TYPE_NOSNIFF=True`, `SECURE_BROWSER_XSS_FILTER=True`, `X_FRAME_OPTIONS='DENY'`.
- HSTS (`SECURE_HSTS_*`) enabled when not in debug; `SECURE_SSL_REDIRECT` respects `DJANGO_DEBUG`.
- `SecurityHeadersMiddleware` sets `X-Content-Type-Options=nosniff`, `Referrer-Policy=strict-origin-when-cross-origin`, and removes `Server` header when possible.
- **Static file security**: WhiteNoise middleware adds `X-Content-Type-Options: nosniff` and cache headers to all static assets (CSS, JS, fonts) via `config/utils/whitenoise_headers.py`

CSP
- Enforced by custom `CustomCSPMiddleware` (config/middleware/csp_custom.py).
- **Route-based policies** for optimal security/compatibility balance:
  - **Admin routes** (`/admin/*`):
    - Relaxed CSP for Django Unfold compatibility
    - Allows `unsafe-inline` and `unsafe-eval` for scripts
    - Allows `unsafe-inline` for styles
    - Google Fonts allowed: `fonts.googleapis.com`, `fonts.gstatic.com`
    - WebSocket support in DEBUG mode (`ws:`, `wss:`)
  - **API/Public routes** (all other paths):
    - Strict CSP with NO `unsafe-inline` or `unsafe-eval`
    - `script-src 'self'`, `style-src 'self'`
    - Frame-ancestors set to `'none'` (clickjacking protection)
    - WebSocket restricted in production
- **Common security directives** (all routes):
  - `default-src 'self'`
  - `frame-ancestors 'none'`
  - `base-uri 'self'`
  - `form-action 'self'`
  - `object-src 'none'`
- **Validation**: Route detection via `request.path.startswith('/admin/')` in middleware
- **Testing**: Manual verification via browser DevTools and ZAP scanner

CORS (Cross-Origin Resource Sharing)
- **Package**: `django-cors-headers==4.4.0`
- **Configuration**: `config/addon/cors.py`
- **Middleware**: `corsheaders.middleware.CorsMiddleware` (positioned before CommonMiddleware)
- **Development mode**:
  - Allows localhost origins on ports 3000, 3001, 4200, 8080, 5173 (React, Angular, Vue, Vite)
  - Automatic detection via `DEBUG=True`
- **Production mode**:
  - Requires explicit whitelist via `CORS_ALLOWED_ORIGINS` environment variable
  - Example: `CORS_ALLOWED_ORIGINS="https://app.kinwise.com,https://www.kinwise.com"`
  - `CORS_ALLOW_ALL_ORIGINS=False` (secure default)
- **Security settings**:
  - `CORS_ALLOW_CREDENTIALS=True` (supports cookie-based auth)
  - Allowed methods: GET, POST, PUT, PATCH, DELETE
  - Allowed headers: authorization, content-type, x-csrftoken
  - Exposed headers: content-type, x-csrftoken
  - Preflight cache: 86400 seconds (24 hours)
- **Testing**: See `config/tests/test_cors.py` for comprehensive CORS validation

Auth & lockout
- **Authentication Backends** (in order):
  1. `users.backends.EmailOrUsernameBackend` - Custom backend supporting email OR username login
  2. `axes.backends.AxesStandaloneBackend` - Brute-force protection with lockout
  3. `django.contrib.auth.backends.ModelBackend` - Django default fallback
- **Lockout Testing**: Tests validate login lockout after failure limit (see `config/tests/test_security_headers.py`)

Session Timeout (Idle Timeout)
- **Implementation**: `config.middleware.session.IdleTimeoutMiddleware`
- **SOC 2 Compliance**: Automatic session expiration after inactivity period
- **Configuration**:
  - `IDLE_TIMEOUT_SECONDS = 15 * 60` (15 minutes of inactivity)
  - `IDLE_GRACE_SECONDS = 2 * 60` (2 minutes grace period)
- **Behavior**:
  - **Idle window** (< 15 min): Activity extends session automatically
  - **Grace window** (15-17 min): Only `/session/ping/` POST extends session
  - **Hard expiry** (> 17 min): Automatic logout with redirect
- **Client Integration**:
  - Response headers: `X-Session-Timeout`, `X-Session-Grace`, `X-Session-Remaining`
  - Frontend countdown timer support
  - Session ping endpoint: `POST /api/v1/session/ping/`
- **Testing**: See `config/middleware/session.py` for implementation details

Cookies & CSRF
- `SESSION_COOKIE_SECURE/HTTPONLY/SAMESITE`, `CSRF_COOKIE_SECURE/HTTPONLY/SAMESITE` tuned per environment.
- `CookieSecurityMiddleware` enforces HttpOnly and SameSite=Strict on session/CSRF cookies.

Security tests (CI expectations)
- Admin responses include `Content-Security-Policy`, `X-Content-Type-Options=nosniff`, `Referrer-Policy=strict-origin-when-cross-origin`.
- CSRF cookie is HttpOnly (and Secure when configured).
- HSTS present for HTTPS requests under HSTS-enabled settings.
- Locked-out user cannot log in after configured failure limit.
 - Rate limiting returns HTTP 429 after exceeding thresholds; see `config/tests/test_ratelimit.py`.

Rate limiting
- Library: Custom middleware (view-level throttling) alongside `django-axes` (account lockout).
- Admin login protection: 4 attempts allowed per minute per IP on `/admin/login/`; 5th attempt returns HTTP 429; Axes still enforces lockout on repeated failures.
- Configuration: cache backends in `config/addon/cache.py`; middleware in `config/utils/ratelimit.py` (`AdminLoginRateLimitMiddleware`).
- Production: use Redis for throttling; set `REDIS_URL` (and optionally `REDIS_URL_RATELIMIT`) to separate stores.
- Testing: see `config/tests/test_ratelimit.py` for rate limit validation.
- API usage (future implementation with django-ratelimit):
	```python
	from django_ratelimit.decorators import ratelimit
	from rest_framework.views import APIView

	class LoginAPIView(APIView):
			@ratelimit(key='ip', rate='5/m', method='POST')
			def post(self, request):
					...
	```
Recommended API limits (baseline)
- Admin login: 4/min/IP (5th blocked)
- API login: 5/min/IP (recommended)
- Registration: 3/hour/IP
- Token refresh: 10/min/user
- List endpoints: 100/hour/user
- Create endpoints: 10–20/hour/user

Compliance
- Implements SOC 2–aligned controls (Availability: rate limiting; Security: headers, CSP, lockout).
- **OWASP ZAP Security Assessment** (November 14, 2025):
  - **Report 4 - Route-Based CSP Implementation**:
    - **HIGH vulnerabilities**: 0 ✅
    - **MEDIUM vulnerabilities**: 5 (WebSocket wildcards in DEBUG, static file CSP, server version)
    - **LOW vulnerabilities**: 2 (X-Content-Type-Options added ✅, server version header)
    - **Validation**: Route-based CSP confirmed working (admin relaxed, API strict)
    - **Admin routes**: Correctly receive relaxed CSP with unsafe-inline/unsafe-eval for Unfold
    - **API routes**: Correctly receive strict CSP with NO unsafe directives
    - **Google Fonts**: Allowed in admin CSP (fonts.googleapis.com, fonts.gstatic.com)
    - **X-Content-Type-Options**: Now set to `nosniff` on all responses ✅
  - **Report 3 - Initial ZAP Assessment**:
    - Identified 5 Medium + 3 Low CSP issues (now resolved via route-based approach)
  - **Production readiness**: Confirmed strict CSP on API endpoints, relaxed only for admin UI
  - **Static file security**: WhiteNoise configured with X-Content-Type-Options headers
  - **Reports**: See `docs/reports/2025-11-14-ZAP-Report-4.md` and `docs/reports/2025-11-14-ZAP-Report-3.md`

---

## Audit Logging

Overview
- Centralized audit logging for critical actions: authentication, CRUD changes, permission/role changes, data exports, bulk operations, and failures with context.
- View logs in Admin at `/admin/audit/auditlog/` with filtering by action type, user, object, household, and date.

When to log
- Always: login/logout/failed attempts, create/update/delete, permission changes, exports, bulk ops, failed ops.
- Skip: read-only (unless sensitive), health checks, static requests.

Service patterns
```python
from audit.services import log_action, log_model_change, log_data_export

# Simple action
log_action(user=request.user, action_type='CREATE', action_description='Created new budget', request=request)

# Model change
log_model_change(user=request.user, action_type='UPDATE', instance=transaction, old_values={'amount': 50.00}, request=request)

# Data export
log_data_export(user=request.user, export_type='transaction_export', record_count=150, request=request, household=household, file_format='csv')
```

DRF integration
- Use a ViewSet mixin (e.g., `transactions.mixins.AuditLoggingMixin`) to automatically log CRUD operations.

Action types
- AUTH: LOGIN, LOGOUT, LOGIN_FAILED, PASSWORD_CHANGE, MFA_ENABLED
- CRUD: CREATE, UPDATE, DELETE, VIEW
- DATA: EXPORT, IMPORT, BULK_DELETE
- PERMISSIONS: PERMISSION_GRANT, PERMISSION_REVOKE, ROLE_CHANGE
- SYSTEM: RATE_LIMIT_EXCEEDED, ACCOUNT_LOCKED, ACCOUNT_UNLOCKED

---

## Applications & Domain Models

### ✅ Implemented Apps (17 Total)

#### Common (`apps/common`) - Foundation
- **Status**: ✅ Complete
- **Models**: `BaseModel` (abstract)
- **Features**:
  - Auto-managed `created_at` (indexed) and `updated_at` timestamps
  - Base for all domain models ensuring consistent audit trail

#### Users (`apps/users`) - Authentication & Authorization
- **Status**: ✅ Complete with MFA, Email Verification, and OTP support
- **Models**: `User`, `UserMFADevice`, `EmailOTP`, `EmailVerification`
- **Features**:
  - **Flexible Authentication**: Email OR username login via custom `EmailOrUsernameBackend`
  - **Email Verification**: Token-based email verification for new registrations (24-hour expiry)
  - **Passwordless Login**: Email OTP (One-Time Password) for secure passwordless authentication (10-minute expiry)
  - **MFA Support**: Time-based OTP (TOTP) via django-otp with backup codes
  - **User Model Features**:
    - UUID for external API references (prevents ID enumeration)
    - Email uniqueness (case-insensitive, normalized to lowercase)
    - Username support (optional, case-insensitive unique)
    - Role-based access control (6 roles: admin, parent, teen, child, flatmate, observer)
    - Multi-locale support (en-nz, en-au, mi-nz, etc.)
    - Optional household FK for primary household
    - Phone number validation (international format)
    - Rate limiting on account creation (prevents automated attacks)
- **Authentication Backends**:
  - `users.backends.EmailOrUsernameBackend` (custom, supports email OR username)
  - `axes.backends.AxesStandaloneBackend` (brute-force protection)
  - `django.contrib.auth.backends.ModelBackend` (fallback)
- **API Endpoints**: 
  - `/api/v1/users/` - User management
  - `/api/v1/auth/token/` - JWT authentication (with MFA support)
  - `/api/v1/auth/register/` - User registration
  - `/api/v1/auth/verify-email/` - Email verification
  - `/api/v1/auth/resend-verification/` - Resend verification email
  - `/api/v1/auth/otp/` - Email OTP endpoints
- **Serializers**: `UserSerializer`, `MFATokenObtainPairSerializer`, `UserRegistrationSerializer`
- **ViewSets**: `UserViewSet`, `EmailOTPViewSet`
- **Celery Tasks**: 
  - `send_verification_email` - Async email verification
  - `send_otp_email` - OTP code delivery
  - `send_welcome_email` - Post-verification welcome
- **Email Templates**: 
  - `templates/emails/verify_email.html`
  - `templates/emails/login_otp.html`
  - `templates/emails/welcome.html`
- **Security**:
  - Password normalization and validation (min 12 chars)
  - Email case-insensitive uniqueness
  - Username case-insensitive uniqueness
  - Indexed on `(email, is_active)` and `(username, is_active)`
  - Full audit logging integration
  - Rate limiting on registration endpoints

#### Households (`apps/households`) - Multi-Tenancy Core
- **Status**: ✅ Complete with service layer
- **Models**: `Household`, `Membership`
- **Purpose**: Core multi-tenant architecture enabling collaborative financial management for diverse household types
- **Features**:
  - **Household Types** (aligned with ICPs):
    - `family` - Family households (ICP1: 2+ adults, kids ages 8-19, $60k-$120k income)
    - `couple` - DINK/SINK couples (ICP2/3: Dual or single income, no kids, $50k-$200k)
    - `student` - Student flats (ICP4: 3-5 flatmates, university students, bill splitting)
    - `individual` - Solo users (ICP5: Single person budgeting, personal finance tracking)
  - **Multi-Household Membership**:
    - Users can belong to multiple households (e.g., family + work team)
    - Primary household designation (automatic on first join)
    - Membership roles per household (admin, parent, teen, child, flatmate, observer)
    - Status lifecycle: active → cancelled/expired
  - **Budget Configuration**:
    - Configurable budget cycles (weekly, fortnightly, monthly, quarterly, yearly, custom)
    - Aligned with income frequency (e.g., fortnightly for most NZ salaries)
  - **Membership & Billing**:
    - Subscription tiers (free, plus, premium)
    - Organisation linkage for B2B/"Whānau Works" members
    - Auto-set `ended_at` on cancellation
  - **ICP-Specific Use Cases**:
    - **Families (ICP1)**: Shared goals, kids' financial education, allowance tracking
    - **DINK Couples (ICP2)**: Proportional expense splitting (70/30), travel funds, investment tracking
    - **SINK Couples (ICP3)**: Single-income budget discipline, emergency fund building
    - **Student Flats (ICP4)**: Bill splitting, StudyLink tracking, irregular income management
    - **Individuals (ICP5)**: Personal goals, simple tracking, learning budgeting basics
- **Service Layer**: `membership_set_primary()`, `membership_create()`, `membership_deactivate()`
- **API Endpoints**: `/api/v1/households/` (via `households.apis`)
- **Serializers**: `HouseholdSerializer`, `HouseholdCreateSerializer`, `MembershipSerializer`
- **Business Rules**:
  - One primary household per user enforced
  - Strict membership status lifecycle (active → cancelled/expired)
  - Auto-set `ended_at` on cancellation
  - Validation prevents inactive primary memberships
- **Target Markets**:
  - **Consumer (B2C)**: Families, couples, students, individuals ($5.99/month Plus tier)
  - **Business (B2B)**: Organizations via "Whānau Works" subscription ($50-$500/month org tiers)

#### Accounts (`apps/accounts`) - Financial Accounts
- **Status**: ✅ Complete
- **Models**: `Account`
- **Features**:
  - Multiple account types (checking, savings, credit, cash, investment)
  - Opening and current balance tracking
  - Credit limit management for credit cards
  - Institution metadata (name, account number masking)
  - Multi-currency support (default NZD)
  - Include/exclude from household totals
  - Active/inactive status
- **API Endpoints**: `/api/v1/accounts/`
- **ViewSets**: `AccountViewSet` with custom `close_account` action
- **Serializers**: `AccountSerializer`, `AccountCreateSerializer`
- **Permissions**: `IsAccountHouseholdMember`
- **Validation**:
  - Non-credit accounts cannot have negative balance
  - Credit accounts require `credit_limit`
  - Credit cards: balance validated against limit
- **Computed Properties**:
  - `available_credit` (for credit cards)
  - `calculated_balance` (opening + sum of transactions)

#### Transactions (`apps/transactions`) - Financial Transaction Tracking
- **Status**: ✅ Complete with service layer, audit integration, and OCR support
- **Models**: `Transaction`, `TransactionTag`, `TransactionAttachment`, `TransactionSplit`
- **Features**:
  - **Transaction Model**:
    - UUID for external API/webhook identification
    - Explicit transaction types (income, expense, transfer)
    - Status tracking (pending, completed, failed, cancelled)
    - Multiple entry sources (manual, voice, receipt, import)
    - Category assignment and flexible tagging (M2M)
    - Goal and budget linkage
    - Transfer pairing via `linked_transaction`
    - Merchant tracking
    - Recurring transaction flag
  - **TransactionAttachment Model**:
    - Receipt image storage (`upload_to='receipts/%Y/%m/'`)
    - OCR processing support via AWS Textract
    - OCR status tracking, confidence scores, and error logging
    - Structured OCR data (merchant, amount, date, items)
    - File validation (size, type)
    - 12-month retention as per spec
    - Uploaded by user tracking
  - **TransactionSplit Model**:
    - Multi-category transaction splitting
    - Household member expense allocation (e.g., flatmate bill splitting)
    - Per-split descriptions and amounts
- **Service Layer**: `transaction_create()`, `transaction_update()`, `transaction_delete()` with audit logging
- **API Endpoints**: `/api/v1/transactions/`
- **ViewSets**: `TransactionViewSet` with custom actions:
  - `link_transfer` - Create paired transfer transaction
  - `add_tags` - Add multiple tags
  - `remove_tag` - Remove tag
  - `receipt_ocr` - OCR processing endpoint (AWS Textract integration)
  - `upload_receipt` - Receipt image upload with validation
  - `voice_input` - Voice entry endpoint (NLP placeholder)
- **Serializers**: `TransactionSerializer`, `TransactionCreateSerializer`, `TransactionTagSerializer`, `TransactionAttachmentSerializer`, `TransactionSplitSerializer`
- **Permissions**: `IsTransactionHouseholdMember`
- **Mixins**: `AuditLoggingMixin` for automatic CRUD audit logging
- **Validation**:
  - Amount cannot be zero
  - Expense must have negative amount
  - Income must have positive amount
  - Transfer requires linked_transaction
  - Budget/goal must belong to same household
  - Receipt file size limit (10MB default, configurable via `RECEIPT_MAX_SIZE_MB`)
  - Receipt file formats: jpg, jpeg, png, pdf
- **Indexing**: Optimized for date-based queries, household filtering, OCR processing status
- **AWS Integration**:
  - S3 storage for receipt images (optional)
  - Textract OCR processing (configurable via `AWS_TEXTRACT_ENABLED`)
  - Timeout and file size limits configurable

#### Categories (`apps/categories`) - Transaction Classification
- **Status**: ✅ Complete with service layer
- **Models**: `Category`
- **Features**:
  - Hierarchical structure (parent/child relationships)
  - Category types (income, expense, both)
  - Soft deletion (preserves transaction history)
  - System-provided default categories
  - Household-specific custom categories
  - UI metadata (icon, color, display order)
  - Usage statistics
- **Service Layer**: `create_default_categories()`, `category_soft_delete()`
- **API Endpoints**: `/api/v1/categories/`
- **ViewSets**: `CategoryViewSet` with filtering (type, active, deleted)
- **Serializers**: `CategorySerializer`, `CategoryCreateSerializer`, `CategoryUpdateSerializer`
- **Permissions**: `IsCategoryHouseholdMember`
- **Validation**:
  - No circular references (self-parent prevention)
  - Parent must belong to same household
  - Unique name per household (case-insensitive)
  - Depth limit enforcement
- **Computed Properties**:
  - `full_path` - Hierarchical path display
  - `has_subcategories` - Child category check
  - Transaction count and total amount
  - Usage statistics
- **Default Categories**: Comprehensive starter set (Income, Housing, Food & Dining, Transportation, Entertainment, Shopping, Health & Wellness, Education, Uncategorized)

#### Budgets (`apps/budgets`) - Budget Planning & Tracking
- **Status**: ✅ Complete
- **Models**: `Budget`, `BudgetItem`
- **Features**:
  - Time-bound budget periods
  - Multiple cycle types (weekly, fortnightly, monthly, quarterly, yearly, custom)
  - Category breakdown via BudgetItems
  - Alert thresholds (default 80%)
  - Rollover support for unused budget
  - Status tracking (active, completed, exceeded, cancelled)
- **API Endpoints**: `/api/v1/budgets/`
- **ViewSets**: `BudgetViewSet`, `BudgetItemViewSet` with custom actions:
  - `utilization` - Budget spending analysis
  - `add_item` - Create budget item
- **Serializers**: `BudgetSerializer`, `BudgetItemSerializer`, `BudgetItemCreateSerializer`
- **Permissions**: `IsBudgetHouseholdMember`, `IsBudgetItemHouseholdMember`
- **Validation**:
  - `start_date` must be before `end_date`
  - `total_amount` must be positive
  - `alert_threshold` must be 0-100%
  - BudgetItem category must match household
- **Computed Properties** (Budget):
  - `is_active` - Currently active check
  - `is_expired` - Period ended check
  - `days_remaining` - Time to end date
  - `get_total_spent()` - Actual spending
  - `get_total_remaining()` - Budget left
  - `get_utilization_percentage()` - Spend %
  - `is_over_budget()` - Exceeded check
  - `should_alert()` - Threshold check
- **Computed Properties** (BudgetItem):
  - `get_spent()` - Category spending
  - `get_remaining()` - Category budget left
  - `get_utilization_percentage()` - Category %
  - `is_over_budget()` - Category exceeded

#### Goals (`apps/goals`) - Savings Goals & Gamification
- **Status**: ✅ Complete with progress tracking
- **Models**: `Goal`, `GoalProgress`
- **Features**:
  - Multiple goal types (savings, debt_payoff, purchase, emergency_fund, investment)
  - Target and current amount tracking
  - Due date management
  - Milestone-based gamification (stickers)
  - Auto-contribution support
  - Visual customization (icon, color, image)
  - Progress history
- **API Endpoints**: `/api/v1/goals/`
- **ViewSets**: `GoalViewSet`, `GoalProgressViewSet` with custom actions:
  - `progress_list` - View goal progress history
  - `add_progress` - Record contribution
- **Serializers**: `GoalSerializer`, `GoalProgressSerializer`
- **Permissions**: `IsGoalHouseholdMember`, `IsGoalProgressHouseholdMember`
- **Validation**:
  - `target_amount` must be positive
  - `current_amount` cannot exceed target
  - `due_date` must be in future (new goals)
  - `contribution_percentage` must be 0-100%
  - `milestone_amount` validation
- **Computed Properties** (Goal):
  - `progress_percentage` - % to target
  - `remaining_amount` - Amount needed
  - `days_remaining` - Time to deadline
  - `is_completed` - Goal reached
  - `is_overdue` - Past due date
  - `expected_milestones` - Total possible
  - `total_contributed` - Sum via GoalProgress

#### Bills (`apps/bills`) - Recurring Bill Management
- **Status**: ✅ Complete with document upload support
- **Models**: `Bill`
- **Features**:
  - Multiple frequencies (weekly, fortnightly, monthly, quarterly, yearly, one_time)
  - Due date tracking
  - Payment status management
  - Transaction linkage
  - Category and account assignment
  - Reminder system (days before)
  - Auto-pay flag
  - Recurring bill generation
  - Document/bill image upload with OCR support
- **API Endpoints**: `/api/v1/bills/`
- **ViewSets**: `BillViewSet` with custom actions:
  - `mark_paid` - Record payment
  - `upcoming` - Bills due soon
  - `overdue` - Overdue bills
  - `scan_bill` - Bill document OCR processing
  - `upload_document` - Upload bill images/PDFs
- **Serializers**: `BillSerializer`
- **Permissions**: `IsBillHouseholdMember`
- **Validation**:
  - `amount` must be positive
  - `paid_date` cannot be before `due_date`
  - Category/account must match household
  - Status 'paid' requires `paid_date`
- **Computed Properties**:
  - `is_overdue` - Past due check
  - `is_upcoming` - Due within 7 days
  - `days_until_due` - Time remaining
  - `should_send_reminder` - Reminder check
  - `calculate_next_due_date()` - Next occurrence

#### Alerts (`apps/alerts`) - Notification System
- **Status**: ✅ Complete
- **Models**: `Alert`
- **Features**:
  - Multiple alert types (budget warnings, bill reminders, goal milestones, etc.)
  - Priority levels (low, medium, high, urgent)
  - Status management (active, dismissed, resolved)
  - Multi-channel delivery (email, push)
  - Action links
  - Related object linkage (budget, bill, account, goal)
  - Dismissal tracking
- **API Endpoints**: `/api/v1/alerts/`
- **Views**: `AlertListView`, `AlertDetailView`, `AlertDismissView`
- **Serializers**: `AlertSerializer`
- **Permissions**: `IsAlertHouseholdMember`
- **Computed Properties**:
  - `is_active` - Active status check
  - `is_high_priority` - High/urgent check

#### Organisations (`apps/organisations`) - B2B/Community Support ("Whānau Works")
- **Status**: ✅ Complete (Admin-only)
- **Models**: `Organisation`
- **Purpose**: Enable B2B and community group financial management for corporate expense tracking, educational institutions, non-profits, and clubs
- **Features**:
  - **Organisation Types**:
    - `corporate` - Corporate expense tracking and employee benefits
    - `non-profit` - Community groups, charities, NGOs
    - `education` - Schools, universities, educational institutions
    - `government` - Government departments and agencies
    - `club` - Sports clubs, social clubs, community organizations
  - **Subscription Management**:
    - Subscription tiers: `ww_starter`, `ww_growth`, `ww_enterprise`
    - Organisation-level billing (not per-member)
    - Payment status tracking (trial, active, overdue, cancelled, suspended)
    - Billing cycle configuration (weekly, monthly, quarterly, yearly)
    - Next billing date tracking
  - **Member Management**:
    - Owner field (legal/billing responsibility, PROTECT on delete)
    - Multiple admins via Membership.role system
    - Member capacity limits (default 50, configurable by tier)
    - Active member count tracking
  - **Financial Configuration**:
    - Financial year start (MM-DD format, e.g., '04-01' for April 1st)
    - Default budget cycle for organisation
    - Multi-currency support (NZD, AUD, USD, GBP, EUR)
  - **Contact & Details**:
    - Primary contact email
    - Optional phone number, address, website
- **Target ICPs**:
  - **Corporate**: Employee expense management, team budgets, department financial tracking
  - **Education**: School clubs, university societies, student organization budgeting
  - **Non-Profit**: Community groups, charity financial management
  - **Clubs**: Sports teams, social clubs, hobby groups with shared expenses
- **API Endpoints**: `/api/v1/organisations/`
- **ViewSets**: `OrganisationViewSet` (admin-only access)
- **Serializers**: `OrganisationSerializer`
- **Permissions**: `IsAdminOnly`
- **Validation**:
  - Financial year start must be valid MM-DD format
  - Owner cannot be deleted while owning active organisations
- **Computed Properties**:
  - `current_member_count` - Active members count
  - `has_capacity` - Can add more members (current < max)
  - `is_trial` - Trial period check
  - `is_paid_up` - Subscription in good standing (payment_status='active')
- **Business Rules**:
  - Organisation-wide settings cascade to all member households
  - Owner has ultimate authority over organisation
  - Admins manage day-to-day operations via Membership roles

#### Rewards (`apps/rewards`) - Gamification Engine
- **Status**: ✅ Complete (Read-only API)
- **Models**: `Reward`
- **Features**:
  - Multiple reward types (milestone, streak, budget_saved, goal_reached)
  - Point system
  - Visual badges
  - Related object linkage
  - Visibility control
- **API Endpoints**: `/api/v1/rewards/`
- **ViewSets**: `RewardViewSet` (read-only)
- **Serializers**: `RewardSerializer`
- **Permissions**: `IsRewardOwnerOrAdmin`

#### Lessons (`apps/lessons`) - Financial Education
- **Status**: ✅ Complete (Read-only API)
- **Models**: `FinancialLesson`
- **Features**:
  - Age-appropriate content (child, teen, young_adult, adult, all)
  - Difficulty levels (beginner, intermediate, advanced)
  - Category organization
  - Multimedia support (images, videos)
  - Duration estimates
  - Publication workflow
  - Search tags
- **API Endpoints**: `/api/v1/lessons/`
- **ViewSets**: `FinancialLessonViewSet` (read-only, published only)
- **Serializers**: `FinancialLessonSerializer`
- **Permissions**: `IsAuthenticatedReadOnly`

#### Audit (`apps/audit`) - Security & Compliance Logging
- **Status**: ✅ Complete with comprehensive service layer
- **Models**: `AuditLog`, `DataExportLog`
- **Features**:
  - Comprehensive action logging (AUTH, CRUD, DATA, PERMISSIONS, SYSTEM)
  - Request metadata capture (IP, user agent, headers)
  - Model change tracking with before/after values
  - Data export audit trail
  - Household and organisation context
  - Staff-only access
- **Service Layer**: `log_action()`, `log_model_change()`, `log_data_export()`
- **API Endpoints**: `/api/v1/audit/`
- **ViewSets**: `AuditLogViewSet` (read-only, staff-only)
- **Serializers**: `AuditLogSerializer`
- **Permissions**: `IsAuditAdmin`
- **Integration**: Automatic logging via `AuditLoggingMixin` for ViewSets

#### Privacy (`apps/privacy`) - GDPR Compliance
- **Status**: ✅ Complete
- **Models**: None (service-based)
- **Features**:
  - User data export (DSAR)
  - Data deletion requests
  - Privacy information API
  - Household-scoped data access
- **Service Layer**: `export_user_data()`, `request_data_deletion()`, `get_data_deletion_status()`
- **API Endpoints**: `/api/v1/privacy/`
- **Views**: `DataExportApi`, `DataDeletionRequestApi`, `PrivacyInfoApi`
- **Security**: Household membership validation, audit logging

#### Reports (`apps/reports`) - Analytics & Exports
- **Status**: ✅ Complete
- **Models**: None (service-based)
- **Features**:
  - Household data export (JSON)
  - Transaction reports
  - Budget analysis
  - Goal tracking
- **API Endpoints**: `/api/v1/reports/`
- **Views**: `HouseholdExportApi`

### Feature Summary by Category

**Financial Management** (5 apps)
- ✅ Accounts - Multi-type account management
- ✅ Transactions - Income/expense/transfer tracking with OCR support and receipt attachments
- ✅ Categories - Hierarchical classification with defaults
- ✅ Budgets - Period-based planning with category breakdown
- ✅ Bills - Recurring payment tracking

**Planning & Goals** (1 app)
- ✅ Goals - Savings goals with milestone gamification

**User & Access Management** (3 apps)
- ✅ Users - Email/username auth with MFA, OTP, and email verification
- ✅ Households - Multi-tenant membership system
- ✅ Organisations - B2B/enterprise support

**Engagement** (3 apps)
- ✅ Rewards - Achievement badges and points
- ✅ Lessons - Financial literacy content
- ✅ Alerts - Multi-channel notifications

**Security & Compliance** (2 apps)
- ✅ Audit - Comprehensive action logging
- ✅ Privacy - GDPR data export/deletion

**Analytics** (1 app)
- ✅ Reports - Data export and analysis

**Foundation** (1 app)
- ✅ Common - Base models and utilities

---

## API v1 Endpoints

All API routes are centralized in `config/api_v1_urls.py` and mounted at `/api/v1/` (configured in `config/urls.py`).

### Authentication Endpoints
- **`POST /api/v1/auth/token/`** – Obtain JWT access/refresh tokens (supports MFA)
- **`POST /api/v1/auth/token/refresh/`** – Refresh JWT access token
- **`POST /api/v1/auth/register/`** – User registration with email verification
- **`POST /api/v1/auth/verify-email/`** – Verify email with token
- **`POST /api/v1/auth/resend-verification/`** – Resend verification email
- **`POST /api/v1/auth/otp/request/`** – Request OTP for passwordless login
- **`POST /api/v1/auth/otp/verify/`** – Verify OTP code
- **`/api/v1/auth/`** – Additional auth endpoints (defined in `users.auth_urls`)
- **`GET /api/v1/session/ping/`** – Session health check (extends session during grace period)

### Developer Tools
- **`GET /api/v1/schema/`** – OpenAPI 3 schema (drf-spectacular)
- **`GET /api/v1/docs/`** – Swagger UI interactive documentation

### Domain Endpoints
Each app exposes its own REST endpoints via `<app>.api_urls` included at the root:

- **`/api/v1/accounts/…`** – Financial accounts management
- **`/api/v1/alerts/…`** – Budget/goal/bill notifications
- **`/api/v1/audit/…`** – Security & compliance logs
- **`/api/v1/bills/…`** – Recurring bills & payment schedules
- **`/api/v1/budgets/…`** – Spending plans & limits
- **`/api/v1/categories/…`** – Transaction classification
- **`/api/v1/goals/…`** – Savings goals & progress
- **`/api/v1/lessons/…`** – Financial literacy content
- **`/api/v1/organisations/…`** – Business/school/club structures
- **`/api/v1/privacy/…`** – GDPR/privacy compliance (consents, data requests)
- **`/api/v1/reports/…`** – Analytics & scheduled reports
- **`/api/v1/rewards/…`** – Gamification (points, badges, rewards)
- **`/api/v1/transactions/…`** – Income/expense records
- **`/api/v1/users/…`** – User profiles, MFA, preferences

> **Note:** Specific endpoint paths, methods, and serializers are defined in each app's `api_urls.py`, `viewsets.py`, and `serializers.py`.

---

## Admin Interface

- Unfold (`django-unfold`) provides a modern admin UI with custom sidebar, titles, and branding.
- Configuration lives in `config/scripts/unfold.py` (navigation groups for Users, Households, Memberships, Accounts, Transactions/Tags, Categories, Budgets/Items, Goals/Progress, Bills, Rewards, Lessons, Alerts).
- Custom static assets can be added under `static/unfold/` and referenced via `UNFOLD["STYLES"|"SCRIPTS"]`.

---

## Development Guide

Local setup (Windows PowerShell)
```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Create .env in repo root (same folder as manage.py)
# e.g. DJANGO_SECRET_KEY=your-secret; DJANGO_DEBUG=True
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Run management utilities
```powershell
python manage.py showmigrations
python manage.py shell
python manage.py collectstatic --noinput
```

Access points
- Admin: http://localhost:8000/admin/
- API: http://localhost:8000/api/v1/
- API Documentation: http://localhost:8000/api/v1/docs/

Celery setup (for async tasks)
```powershell
# Ensure Redis is running (required for Celery broker)
# Install Redis on Windows or use Docker

# Start Celery worker (in separate terminal)
celery -A config worker -l info

# Start Celery beat for scheduled tasks (in separate terminal)
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

---

## Async Task Queue (Celery)

KinWise uses Celery for asynchronous task processing, enabling non-blocking operations for email delivery, OCR processing, and scheduled jobs.

### Configuration
- **Broker**: Redis (default: `redis://localhost:6379/0`)
- **Result Backend**: Redis (stores task results)
- **Serialization**: JSON (secure, cross-language compatible)
- **Scheduler**: django-celery-beat (database-backed scheduling)
- **Task Routing**: Organized by app (users, bills, goals queues)

### Implemented Tasks

**User Tasks** (`users.tasks`)
- `send_verification_email(user_id, verification_token)` - Email verification links
- `send_otp_email(user_id, otp_code)` - OTP codes for passwordless login
- `send_welcome_email(user_id)` - Post-verification welcome emails
- **Features**: Retry with exponential backoff, HTML email templates, error handling

**Scheduled Tasks** (via Celery Beat)
- `bills.tasks.send_bill_reminders` - Daily at 9 AM (bill payment reminders)
- `goals.tasks.check_goal_milestones` - Daily at 10 AM (goal progress notifications)

### Task Management
```python
# Queue a task
from users.tasks import send_verification_email
result = send_verification_email.delay(user_id=123, verification_token="abc-123")

# Check task status
result.status  # 'PENDING', 'STARTED', 'SUCCESS', 'FAILURE'

# Get result (blocks until complete)
result.get(timeout=10)
```

### Monitoring
- **Admin Interface**: `/admin/django_celery_beat/` for scheduled task management
- **Task Results**: Stored in `django_celery_results_taskresult` table
- **Flower** (optional): Real-time Celery monitoring dashboard

### Configuration Settings
```python
# config/settings/base.py
CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes max
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes soft limit
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Task routes by app
CELERY_TASK_ROUTES = {
    "users.tasks.*": {"queue": "users"},
    "bills.tasks.*": {"queue": "bills"},
    "goals.tasks.*": {"queue": "goals"},
}
```

---

## Testing & Quality

### Test Coverage: 97.25% (December 2025)

**Total Metrics:**
- **Coverage**: 97.25% (11,986 statements total, 293 missed)
- **Tests**: 837 passing (0 failures, 15 skipped)
- **Test Files**: 110+ test files across all apps
- **Quality Gates**: All validation logic, business rules, and security controls tested
- **Improvement**: +3.58 percentage points from 93.67% (October 2025)
- **Uncovered Lines**: 293 (reduced from 666, -56% reduction)
- **Files with 100% Coverage**: 211

### SonarQube Integration

**Code Quality Platform:**
- **Tool**: SonarQube (latest) running in Docker container
- **Setup**: Full Docker Compose orchestration with persistent volumes
- **Management**: PowerShell (sonar-docker.ps1) and Bash (run-sonar.sh) scripts
- **CI/CD**: GitHub Actions workflow configured (`.github/workflows/sonarqube.yml`)
- **Quality Gates**: Coverage >80%, no security vulnerabilities
- **Documentation**: See `docs/SONARQUBE_SETUP.md`

**Run SonarQube Analysis:**
```powershell
# Start SonarQube server
.\sonar-docker.ps1 -Action Start

# Generate coverage and run analysis
.\sonar-docker.ps1 -Action Analyze

# View results at http://localhost:9000
```

**Docker Configuration:**
- Container: `kinwise-sonarqube`
- Volumes: Persistent data, extensions, logs
- Network: Isolated `sonarqube-network`
- Port: 9000:9000
- Health Checks: Automatic readiness detection

Run tests
```powershell
pytest  # Run all tests
pytest --cov=apps --cov-report=term-missing  # Run with coverage report
pytest --cov=apps --cov-report=html  # Generate HTML coverage report (htmlcov/)
pytest apps/budgets/tests/  # Run specific app tests
pytest -k "test_validation"  # Run tests matching pattern
```

### Test Coverage by App

**100% Coverage (Perfect):**
- ✅ `budgets/models.py` - 98 statements (Budget, BudgetItem validation & business logic)
- ✅ `budgets/serializers.py` - 52 statements (all serializers)
- ✅ `budgets/permissions.py` - 15 statements (household member checks)
- ✅ `categories/serializers.py` - 36 statements (all serializers)
- ✅ `categories/services.py` - 25 statements (soft delete, defaults)
- ✅ `goals/permissions.py` - 12 statements (household member checks)
- ✅ `bills/permissions.py` - 8 statements (household member checks)
- ✅ `common/views.py` - 100% (session views, admin logout)
- ✅ `config/middleware/session.py` - 97% (session timeout middleware)
- ✅ `config/middleware/security.py` - 100% (security headers)
- ✅ `config/utils/test_utils.py` - 100% (test utilities)
- ✅ `config/utils/whitenoise_headers.py` - 100% (static file security)
- ✅ All test files - 100% test code coverage

**90%+ Coverage (Excellent):**
- ✅ `bills/models.py` - 90% (79 statements, 8 missed - mostly admin methods)
- ✅ `goals/models.py` - 92% (104 statements, 8 missed - mostly admin/edge cases)
- ✅ `categories/models.py` - 93% (68 statements, 5 missed - display methods)
- ✅ `accounts/models.py` - 92% (25 statements, 2 missed - str methods)
- ✅ `households/admin.py` - 93% (30 statements, 2 missed - admin config)
- ✅ `audit/models.py` - 93% (73 statements, 5 missed - admin methods)
- ✅ All ViewSets - 95%+ (comprehensive API integration tests)

**Key Test Coverage Areas:**
- **Model Validation**: All `clean()` methods fully tested (100%)
- **Business Logic**: All computed properties and methods tested
- **Permissions**: All household isolation checks validated
- **Serializers**: All create/update/validation logic tested
- **Services**: All business logic service methods tested
- **Edge Cases**: Zero values, None handling, boundary conditions
- **Security**: Authentication, authorization, CORS, CSP, rate limiting, CSRF
- **ViewSets**: Integration tests for all CRUD operations and custom actions
- **Middleware**: Session timeout, security headers, CSP routing

### Test Organization

**Security Tests** (60+ tests - `config/tests/`):
- `test_phase2_security.py` - CSP, headers, cookies, middleware (30 tests)
- `test_security_headers.py` - HSTS, lockout, rate limiting
- `test_cors.py` - CORS configuration and integration (19 tests)
- `test_ratelimit.py` - Rate limiting validation
- `test_csp_config.py` - CSP policy validation
- `test_session_ping.py` - Session health check and CSRF protection (5 tests)

**ViewSet Integration Tests** (68+ tests across apps):
- `accounts/tests/test_account_viewset.py` - Account CRUD operations (15 tests)
- `alerts/tests/test_alert_viewset.py` - Alert management (6 tests)
- `bills/tests/test_bill_viewset.py` - Bill management (9 tests)
- `budgets/tests/test_budget_viewset.py` - Budget operations (17 tests)
- `categories/tests/test_category_viewset.py` - Category CRUD (12 tests)
- `goals/tests/test_goal_viewset.py` - Goal tracking (9 tests)

**Model Validation Tests** (84+ tests across apps):
- `test_bill_validation.py` - Bill clean() validation (8 tests)
- `test_bill_properties.py` - Bill property edge cases (5 tests)
- `test_budget_models.py` - Budget & BudgetItem (48 tests)
- `test_goal_validation.py` - Goal clean() validation (11 tests)
- `test_goal_methods.py` - Goal method edge cases (5 tests)
- `test_category_validation.py` - Category clean() validation (6 tests)
- `test_account_serializers.py` - Account serializer tests (1 test)

**Middleware Tests** (25+ tests):
- `test_session_middleware.py` - Session timeout logic (15 tests)
- `test_security_middleware.py` - Security headers (10 tests)

**Utility Tests** (20+ tests):
- `test_test_utils.py` - Test helper functions (19 tests)
- `test_whitenoise_headers.py` - Static file security

**Business Logic Tests** (100+ tests):
- Household services (membership, primary designation)
- Category services (soft delete, default creation)
- Transaction services (CRUD with audit logging)
- Budget calculations (spent, remaining, utilization)
- Goal progress tracking and milestones

**Permission Tests** (50+ tests):
- Household-based data isolation
- Role-based access control
- Cross-household prevention
- Staff-only access

**API Tests** (40+ tests):
- Authentication and JWT tokens
- Serializer validation
- ViewSet CRUD operations
- Custom actions and filters

### Quality Assurance Practices

**Test Standards:**
- All tests use `@pytest.mark.django_db` for database access
- All tests use `@pytest.mark.unit` classification
- Descriptive test names following pattern: `test_<method>_<scenario>`
- Comprehensive docstrings explaining test purpose
- Edge case coverage (None, zero, negative, boundary values)
- Fixtures for reusable test data

**Continuous Integration:**
- All tests run on every commit
- Coverage reports generated automatically
- Failed tests block deployment
- Security tests mandatory for production

**Test Documentation:**
- See `docs/testing/QA_GUIDE.md` for comprehensive QA documentation
- See `docs/testing/TEST_COVERAGE_REPORT.md` for detailed coverage analysis
- See individual test files for specific test scenarios

Security tests enforced in `config/tests/test_security_headers.py` and `test_phase2_security.py`
- CSP header present on admin pages
- `X-Content-Type-Options=nosniff`, `Referrer-Policy=strict-origin-when-cross-origin`
- CSRF cookie HttpOnly (and Secure when configured)
- HSTS present for HTTPS responses when enabled
- Axes lockout prevents login after repeated failures
- Cookie SameSite policy enforcement

CORS tests enforced in `config/tests/test_cors.py`
- CORS middleware installed and positioned correctly (before CommonMiddleware)
- Credentials allowed for cookie-based authentication
- Preflight requests handled with proper Access-Control headers
- Development mode allows localhost origins (ports 3000, 3001, 4200, 8080, 5173)
- Production mode requires explicit whitelist (no CORS_ALLOW_ALL_ORIGINS)
- Dangerous headers blocked (e.g., Set-Cookie not in CORS_ALLOW_HEADERS)

CSRF Protection tests enforced in `config/tests/test_session_ping.py`
- SessionPingView requires CSRF token (no @csrf_exempt)
- admin_logout requires POST with CSRF token
- All session endpoints enforce CSRF validation
- Rate limiting on session endpoints (30/minute)

SonarQube Integration
- Continuous code quality monitoring
- Security vulnerability scanning
- Code smell detection
- Test coverage tracking
- Quality gate enforcement

Static analysis & formatting
```powershell
black apps config
flake8 apps config
mypy apps
```

---

## Migrations & Data

Create/apply migrations
```powershell
python manage.py makemigrations
python manage.py migrate
```

Rollback (per app)
```powershell
python manage.py migrate <app> <migration_name>
```

Fixtures (optional)
```powershell
python manage.py dumpdata > backup.json
python manage.py loaddata backup.json
```

---

## Known Issues & User Feedback Analysis

Based on user feedback and production monitoring, the following issues have been identified and prioritized for resolution:

### Critical Severity Issues (Immediate Action Required)

**1. Login Issues** - 28 mentions
- **Symptoms**: Users unable to authenticate, token expiration errors, session loss
- **Backend Implications**:
  - Session timeout (15 min idle + 2 min grace) may be too aggressive for some users
  - JWT token rotation causing frontend sync issues
  - Email/username backend case-sensitivity edge cases
  - Rate limiting (4 attempts/min) blocking legitimate users on slow connections
- **Recommended Fixes**:
  - Add configurable session timeout per user preference
  - Implement token refresh grace period for frontend
  - Add detailed error messages to JWT authentication responses
  - Review rate limiting thresholds (consider 10/min for token endpoints)
  - Add login attempt analytics to identify patterns
- **Related Code**: `users.backends.EmailOrUsernameBackend`, `users.views_auth.MFATokenObtainPairView`, `config/middleware/session.py`

**2. Account Lockout** - 2 mentions
- **Symptoms**: Users locked out after failed attempts, unclear recovery process
- **Backend Implications**:
  - Axes lockout (5 failures, 1 hour cooldown) with no self-service unlock
  - No email notification on lockout
  - Admin-only unlock capability
- **Recommended Fixes**:
  - Implement automated email notification on lockout with unlock link
  - Add "Forgot Password" flow to reset lockout counter
  - Provide user-facing lockout status API endpoint
  - Consider reducing cooldown to 30 minutes for first offense
  - Add Celery task to email admins on repeated lockouts
- **Related Code**: `axes.middleware.AxesMiddleware`, `config/security.py` (AXES_FAILURE_LIMIT, AXES_COOLOFF_TIME)

**3. App Crashes** - 14 mentions
- **Symptoms**: Unexpected application termination, error screens
- **Backend Implications**:
  - Unhandled exceptions in API endpoints
  - Database transaction rollback failures
  - OCR processing (AWS Textract) timeouts causing 500 errors
  - Celery task failures not gracefully handled
- **Recommended Fixes**:
  - Add comprehensive exception handling to all ViewSets
  - Implement circuit breaker pattern for AWS Textract calls
  - Add timeout handling for Celery tasks (currently 30 min max)
  - Improve error responses with user-friendly messages
  - Set up Sentry error tracking for production monitoring
- **Related Code**: All ViewSets, `transactions.viewsets` (OCR endpoints), `config/celery.py`

### High Severity Issues (Next Sprint)

**4. UI/UX Problems** - 50 mentions
- **Symptoms**: Confusing interfaces, unclear workflows, accessibility issues
- **Backend Implications**:
  - API responses lack sufficient metadata for UI state management
  - Serializers not providing computed properties needed for frontend
  - Permissions errors return generic 403 without context
- **Recommended Fixes**:
  - Add `_meta` field to all list responses (pagination, filters, counts)
  - Include `available_actions` array in serializers based on user permissions
  - Enhance error responses with `error_code`, `user_message`, `dev_details`
  - Add API documentation examples to Swagger UI
  - Implement preflight endpoint to check permissions before form submission
- **Related Code**: All serializers, `config/addon/rest_framework.py`, DRF exception handlers

**5. Loading Problems** - 22 mentions
- **Symptoms**: Slow page loads, API timeouts, infinite spinners
- **Backend Implications**:
  - N+1 query issues in nested serializers
  - Missing database indexes on frequently queried fields
  - Large payload sizes (no pagination on some endpoints)
  - OCR processing blocks response (should be async)
- **Recommended Fixes**:
  - Add `select_related()` and `prefetch_related()` to all ViewSets
  - Implement cursor-based pagination for transaction lists
  - Add database indexes on foreign keys and date fields
  - Move OCR processing to Celery background task (return task ID)
  - Enable response compression (gzip middleware)
  - Add query performance logging in development
- **Related Code**: All ViewSets (querysets), `transactions.viewsets`, database indexes

**6. Performance** - 12 mentions
- **Symptoms**: Slow API responses, delayed notifications, laggy dashboards
- **Backend Implications**:
  - Redis caching underutilized (only for rate limiting)
  - No caching on frequently accessed endpoints (categories, lessons, rewards)
  - Computed properties recalculated on every request
  - Large SQL queries not optimized
- **Recommended Fixes**:
  - Implement Django cache decorators on read-only ViewSets
  - Cache category tree, lessons, rewards (invalidate on update)
  - Add Redis caching for Budget utilization calculations
  - Optimize SQL with `only()` and `defer()` for large querysets
  - Add database connection pooling (pgbouncer for Postgres)
  - Implement API response caching with ETags
- **Related Code**: `config/addon/cache.py`, all ViewSets, computed properties

### Medium Severity Issues (Backlog)

**7. Feature Limitations** - 49 mentions
- **Symptoms**: Missing functionality, workarounds required, incomplete features
- **Backend Status**: Many features have backend support but need frontend implementation
- **Areas to Review**:
  - Voice input (NLP endpoint exists but not connected)
  - Receipt OCR (AWS Textract configured but needs async processing)
  - Bill payment automation (structure exists, needs scheduling)
  - Goal milestone notifications (Celery task exists, needs trigger logic)
  - Transaction splits (model exists, needs UI/API integration)
- **Recommended Actions**:
  - Audit existing API endpoints vs frontend feature usage
  - Document placeholder endpoints that need implementation
  - Prioritize by ICP needs (family goals > student splits > DINK investments)
- **Related Code**: `transactions.viewsets.voice_input`, `bills.viewsets.scan_bill`, `config/celery.py`

**8. Browser Issues** - 44 mentions
- **Symptoms**: Cross-browser compatibility, cookie issues, CORS errors
- **Backend Implications**:
  - SameSite=Strict cookies blocking some legitimate cross-site scenarios
  - CORS preflight failures on OPTIONS requests
  - Session cookie domain mismatch (localhost vs 127.0.0.1)
  - Browser-specific CSP violations
- **Recommended Fixes**:
  - Review SameSite cookie policy (consider Lax for session cookies)
  - Ensure CORS middleware handles all HTTP methods
  - Add environment-specific cookie domain configuration
  - Test CSP directives across Chrome, Firefox, Safari, Edge
  - Add browser detection for troubleshooting logs
- **Related Code**: `config/security.py` (cookie settings), `config/addon/cors.py`, `config/middleware/csp_custom.py`

### Action Plan

**Immediate (This Week)**
1. Add detailed logging to login flow for debugging
2. Implement lockout email notifications via Celery
3. Add comprehensive exception handling to crash-prone endpoints

**Short-term (This Sprint)**
4. Optimize database queries with select_related/prefetch_related
5. Implement Redis caching on read-heavy endpoints
6. Add API response metadata for better frontend UX

**Medium-term (Next Sprint)**
7. Move OCR processing to async Celery tasks
8. Implement feature completion (voice, OCR, splits)
9. Add performance monitoring and alerting

### Monitoring & Metrics

**Recommended Additions:**
- **Error Tracking**: Integrate Sentry for production error monitoring
- **Performance Monitoring**: Add Django Debug Toolbar for development, New Relic for production
- **User Analytics**: Track login success rates, session duration, API endpoint usage
- **Database Monitoring**: Add slow query logging, connection pool metrics
- **Celery Monitoring**: Set up Flower dashboard for task queue visibility

---

## Troubleshooting

- Missing CSP header: ensure `csp.middleware.CSPMiddleware` is present (base.py) and CSP settings loaded (`config/settings/security.py`).
- CSRF cookie not HttpOnly/Secure: check `CSRF_COOKIE_HTTPONLY/SECURE` in security settings and environment debug flags.
- Lockout not triggering: verify `django-axes` is installed and backend order (`AxesStandaloneBackend` first).
- Admin assets blocked by CSP: add nonces or allow-lists via `config/addon/csp.py` (keep restrictive by default).
- Using Postgres: set `DATABASE_URL` (e.g., `postgres://...`) and run migrations.
- CORS errors in frontend:
  - **Development**: Verify `DEBUG=True` and frontend runs on localhost:3000/3001/4200/8080/5173
  - **Production**: Set `CORS_ALLOWED_ORIGINS="https://app.kinwise.com,https://www.kinwise.com"` environment variable
  - **Credentials issues**: Ensure `CORS_ALLOW_CREDENTIALS=True` in `config/addon/cors.py`
  - **Preflight failures**: Check CORS middleware is positioned before CommonMiddleware in `config/settings/base.py`

---

## Security Implementation Summary

### ✅ Implemented Security Controls

#### Authentication & Authorization
- ✅ **Email-based authentication** - No username, case-insensitive email
- ✅ **JWT tokens** - Access/refresh token rotation via SimpleJWT
- ✅ **MFA support** - Time-based OTP via django-otp
- ✅ **Role-based access control** - 6 permission levels (admin → observer)
- ✅ **Multi-tenant isolation** - Household-scoped data access
- ✅ **Permission classes** - Per-endpoint household membership validation

#### Account Protection
- ✅ **Account lockout** - django-axes (5 failures, 1 hour cooldown)
- ✅ **Rate limiting** - Custom middleware on admin login (4 attempts/min/IP, 5th blocked)
- ✅ **Session management** - Configurable timeout with grace period
- ✅ **Password security** - Django PBKDF2 hashing

#### Transport & Headers
- ✅ **HTTPS enforcement** - `SECURE_SSL_REDIRECT` in production
- ✅ **HSTS** - 1 year with subdomains and preload
- ✅ **Secure cookies** - HttpOnly, Secure, SameSite=Strict flags
- ✅ **Content Security Policy** - Environment-specific (dev: relaxed, prod: strict)
- ✅ **X-Content-Type-Options** - nosniff protection
- ✅ **X-Frame-Options** - DENY (clickjacking prevention)
- ✅ **Referrer-Policy** - strict-origin-when-cross-origin
- ✅ **Permissions-Policy** - Restricts geolocation, microphone, camera, payment, USB
- ✅ **Server header removal** - Version disclosure prevention (via middleware)

**Middleware Stack** (config/settings/base.py):
1. `CorsMiddleware` - Cross-Origin Resource Sharing (before all)
2. `SecurityMiddleware` - Django core security
3. `SecurityHeadersMiddleware` - Custom headers (X-Content-Type-Options, Referrer-Policy, Permissions-Policy, Server removal)
4. `CustomCSPMiddleware` - Route-based Content Security Policy
5. `SessionMiddleware` - Session management
6. `CommonMiddleware` - Basic HTTP handling
7. `CsrfViewMiddleware` - CSRF protection
8. `AxesMiddleware` - Account lockout
9. `AuthenticationMiddleware` - User authentication
10. `MessageMiddleware` - Message framework
11. `ClickjackingMiddleware` - X-Frame-Options
12. `LocaleMiddleware` - Internationalization
13. `AdminLoginRateLimitMiddleware` - Admin login rate limiting

**CSP Configuration** (config/middleware/csp_custom.py):
- **Admin routes** (`/admin/*`): Relaxed CSP for Django Unfold
  - `script-src 'self' 'unsafe-inline' 'unsafe-eval'`
  - `style-src 'self' 'unsafe-inline' https://fonts.googleapis.com`
  - `font-src 'self' data: https://fonts.gstatic.com`
  - `connect-src 'self' ws: wss:` (DEBUG mode only)
- **API/Public routes**: Strict CSP
  - `script-src 'self'` (no unsafe directives)
  - `style-src 'self'` (no unsafe directives)
  - `font-src 'self'`
  - `connect-src 'self'` (production)
- **Common directives**: `frame-ancestors 'none'`, `base-uri 'self'`, `form-action 'self'`, `object-src 'none'`
- **X-Content-Type-Options**: Added to all responses via middleware

#### Audit & Compliance
- ✅ **Comprehensive audit logging** - All CRUD, auth, permission changes
- ✅ **Request metadata capture** - IP, user agent, timestamp
- ✅ **Model change tracking** - Before/after values
- ✅ **Data export logging** - GDPR compliance trail
- ✅ **Staff-only audit access** - Admin interface and API

#### Data Protection
- ✅ **Multi-tenant isolation** - Household-based data scoping
- ✅ **Soft deletion** - Category preservation for transaction history
- ✅ **CSRF protection** - Token validation on all state-changing operations
- ✅ **GDPR compliance** - Data export and deletion APIs
- ✅ **Field validation** - Model-level `clean()` methods
- ✅ **Transaction atomicity** - `@transaction.atomic` decorators

#### CSRF Protection
- ✅ **CSRF tokens required** - All state-changing operations validated
- ✅ **SessionPingView protection** - Session health check enforces CSRF (removed @csrf_exempt)
- ✅ **POST-only logout** - admin_logout changed from GET/POST to POST-only with CSRF
- ✅ **Rate limiting** - 30 requests/minute on session endpoints
- ✅ **No unsafe exemptions** - All @csrf_exempt decorators removed from session views
- ✅ **Comprehensive tests** - 5 tests in `config/tests/test_session_ping.py`

**SessionPingView Security:**
```python
class SessionPingView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [SessionPingThrottle]
    # NO @csrf_exempt - CSRF token required for security
```

**Admin Logout Security:**
```python
@require_POST  # POST-only, no GET
def admin_logout(request):
    # CSRF token required via POST
    logout(request)
    return HttpResponseRedirect("/admin/login/")
```

#### API Security
- ✅ **Permission enforcement** - IsAuthenticated + custom permissions
- ✅ **Household scoping** - Automatic queryset filtering
- ✅ **Input validation** - Serializer validation + model clean()
- ✅ **OpenAPI documentation** - drf-spectacular schema generation
- ✅ **CORS configuration** - django-cors-headers with whitelist

### Security Test Coverage (60+ tests total)

**Phase 3 Security Tests** (config/tests/test_phase2_security.py - 30 tests):
- ✅ CSP configuration validation (no wildcards, frame-ancestors, base-uri)
- ✅ Security headers present (X-Content-Type-Options, Referrer-Policy, Permissions-Policy, X-Frame-Options)
- ✅ CSP header presence on all endpoints
- ✅ Cookie security flags (HttpOnly, Secure, SameSite=Strict)
- ✅ Server header removal middleware loaded
- ✅ Static file security headers
- ✅ Middleware order validation
- ✅ Production CSP strictness (no unsafe-inline/unsafe-eval)

**CSRF Protection Tests** (config/tests/test_session_ping.py - 5 tests):
- ✅ SessionPingView requires authentication
- ✅ SessionPingView enforces CSRF token
- ✅ Rate limiting on session endpoints (30/minute)
- ✅ POST-only admin logout
- ✅ Proper error responses

**CORS Tests** (config/tests/test_cors.py - 19 tests):
- ✅ CORS middleware positioning
- ✅ Preflight handling
- ✅ Credentials support
- ✅ Development/production mode switching
- ✅ Header whitelisting

**Original Security Tests** (13 tests):
- ✅ HSTS header validation
- ✅ Account lockout after failures
- ✅ Rate limiting (429 responses)
- ✅ Household data isolation
- ✅ API authentication
- ✅ Transaction permissions

### SOC 2 Control Mapping

**CC6.1 - Logical Access Controls**
- ✅ MFA implementation
- ✅ Role-based permissions
- ✅ Account lockout (Axes)
- ✅ Session timeout

**CC6.6 - Restricted Access**
- ✅ Household-based multi-tenancy
- ✅ Permission classes per endpoint
- ✅ Staff-only admin access

**CC6.7 - Restricted Access to Data**
- ✅ Queryset filtering by household
- ✅ Permission validation on object access

**CC7.2 - System Monitoring**
- ✅ Comprehensive audit logging
- ✅ Failed login tracking
- ✅ Rate limit violation logging

**A1.2 - Availability**
- ✅ Rate limiting (DoS prevention)
- ✅ Redis caching support
- ✅ Database connection pooling ready

## Roadmap

### ✅ Completed Phases

**Phase 1: Rate Limiting** — ✅ COMPLETE (100%)
- Admin login protection (5/min/IP)
- Redis-backed throttling
- Custom middleware integration
- See `docs/RATE_LIMITING.md`

**Phase 2: Audit Logging** — ✅ COMPLETE (100%)
- Service layer implementation
- ViewSet mixin automation
- Model change tracking
- Data export logging

**Phase 3: Security Headers & CSP** — ✅ COMPLETE (100%)
- Content Security Policy (CSP) hardening (config/addon/csp.py)
- Environment-specific CSP (development vs production)
- Nonce-based inline script/style support
- Cookie security flags (HttpOnly, Secure, SameSite=Strict)
- Security headers middleware (X-Content-Type-Options, Referrer-Policy, Permissions-Policy)
- Server header suppression
- 30 comprehensive security tests (config/tests/test_phase2_security.py)
- See `docs/V2_SECURITY_ASSESSMENT.md` and `docs/IMPLEMENTATION_GUIDE.md`
- See `docs/AUDIT_LOGGING_GUIDE.md`

**Phase 4: Route-Based CSP Implementation** — ✅ COMPLETE (100%)
- Custom CSP middleware with path-based detection (config/middleware/csp_custom.py)
- Admin routes (/admin/*): Relaxed CSP for Django Unfold compatibility
  - Allows unsafe-inline, unsafe-eval for scripts
  - Google Fonts support (fonts.googleapis.com, fonts.gstatic.com)
  - WebSocket support in DEBUG mode
- API/Public routes: Strict CSP with NO unsafe directives
  - script-src 'self', style-src 'self'
  - No unsafe-inline, no unsafe-eval
- X-Content-Type-Options: nosniff added to all responses
- LOGIN_REDIRECT_URL configuration for admin flow
- ZAP Report 4 validation (0 HIGH vulnerabilities)
- See `docs/reports/2025-11-14-ZAP-Report-4.md`

**Phase 3: MFA Implementation** — ✅ COMPLETE (100%)
- django-otp integration
- TOTP-based 2FA
- JWT + MFA serializer
- User MFA management endpoints

**Phase 4: Session Management** — ✅ COMPLETE (100%)
- Configurable timeout
- Grace period warnings
- Admin UI integration
- Context processor

**Phase 5: API Development** — ✅ COMPLETE (100%)
- All 17 apps with REST APIs
- JWT authentication
- OpenAPI schema (drf-spectacular)
- Swagger UI at `/api/v1/docs/`
- Permission classes per endpoint
- Service layer pattern

**Phase 6: 97.25% Test Coverage** — ✅ COMPLETE (100%)
- ViewSet integration tests (68 tests across 6 apps)
- Middleware coverage improvement (session: 97%, security: 100%)
- Utility test coverage (test_utils: 100%, whitenoise: 100%)
- Overall coverage: 93.67% → 97.25%
- Uncovered lines: 666 → 293 (-56% reduction)
- Total tests: 837 passing, 15 skipped, 0 failures

**Phase 7: SonarQube Integration** — ✅ COMPLETE (100%)
- Docker Compose setup with persistent volumes
- PowerShell and Bash management scripts
- GitHub Actions CI/CD workflow
- Quality gate configuration (coverage >80%, no vulnerabilities)
- SonarQube server running at localhost:9000
- See `docs/SONARQUBE_SETUP.md`

**Phase 8: CSRF Security Hardening** — ✅ COMPLETE (100%)
- Removed @csrf_exempt from SessionPingView
- Changed admin_logout to POST-only with CSRF enforcement
- Updated all documentation with CSRF best practices
- All 60+ security tests passing
- Zero CSRF vulnerabilities remaining

### 📋 Future Enhancements

**Advanced Features**
- [ ] Receipt OCR implementation (placeholder exists)
- [ ] Voice transaction parsing (placeholder exists)
- [ ] Bank feed integration
- [ ] Recurring transaction automation
- [ ] Email/SMS notifications (infra ready)
- [ ] Real-time alerts via WebSockets

**Analytics**
- [ ] Spending trend analysis
- [ ] Budget forecasting
- [ ] Category insights
- [ ] Goal achievement predictions

**Integrations**
- [ ] Calendar sync (bill due dates)
- [ ] Mobile app (React Native)
- [ ] Slack/Discord webhooks
- [ ] Third-party accounting software

**Performance**
- [ ] GraphQL API layer
- [ ] Background job queue (Celery)
- [ ] Advanced caching strategies
- [ ] Database query optimization

**Compliance**
- [ ] SOC 2 Type II certification
- [ ] PCI DSS for payment processing
- [ ] Multi-region data residency

---

Document version: 2.7
Last updated: December 2025
Maintained by: KinWise Backend Team
Status: Production-Ready ✅

**Achievement Highlights:**
- 🎯 97.25% Test Coverage (837 tests)
- 🔒 Zero High Security Vulnerabilities
- 📊 SonarQube Code Quality Monitoring
- ✅ CSRF Protection Fully Enforced
- 🚀 293 Uncovered Lines (down 56% from 666)

**Related Documentation:**
- [Quality Assurance Guide](testing/QA_GUIDE.md) - Comprehensive testing documentation
- [Test Coverage Report](testing/TEST_COVERAGE_REPORT.md) - Detailed coverage analysis
- [Security Assessment](V2_SECURITY_ASSESSMENT.md) - Security audit and compliance
- [Rate Limiting Guide](RATE_LIMITING.md) - API throttling documentation
- [Audit Logging Guide](AUDIT_LOGGING_GUIDE.md) - Compliance logging guide

---

## Phase Implementation Status

### Security Implementation Timeline

| Phase | Feature | Status | Completion Date |
|-------|---------|--------|----------------|
| 1 | Rate Limiting | ✅ Complete | Nov 10, 2025 |
| 2 | Audit Logging | ✅ Complete | Nov 11, 2025 |
| 3 | Security Headers & CSP | ✅ Complete | Nov 12, 2025 |
| 3.5 | CORS Implementation | ✅ Complete | Nov 13, 2025 |
| 4 | Route-Based CSP | ✅ Complete | Nov 14, 2025 |
| 5 | API Authentication | ✅ Complete | Nov 8, 2025 |
| 6 | MFA Implementation | ✅ Complete | Nov 9, 2025 |
| 7 | 97.25% Test Coverage | ✅ Complete | Dec 2025 |
| 8 | SonarQube Integration | ✅ Complete | Dec 2025 |
| 9 | CSRF Hardening | ✅ Complete | Dec 2025 |

### Next Priority Items

**Production Hardening**:
- [ ] Server version header suppression (requires Gunicorn/uWSGI configuration)
- [ ] WebSocket CSP restriction (remove ws:/wss: wildcards in production)
- [ ] Static file CSP headers (ensure all static assets have CSP)

**Advanced Security**:
- [ ] API rate limiting with django-ratelimit
- [ ] Advanced monitoring and alerting
- [ ] Incident response procedures
- [ ] Security automation (dependency scanning, SAST)

**Feature Development**:
- [ ] Receipt OCR implementation
- [ ] Voice transaction parsing
- [ ] Bank feed integration
- [ ] Real-time notifications
