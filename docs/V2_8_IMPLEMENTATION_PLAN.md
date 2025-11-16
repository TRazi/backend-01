# KinWise V2.7 → V2.8 Feature Implementation Plan

**Target Features**:
1. ✅ Celery Integration - Asynchronous task processing
2. ✅ Frontend-Ready User Registration API
3. ✅ Email OTP Login (Passwordless Authentication)
4. ✅ Email Verification System

**Timeline**: 4-6 hours of focused development  
**Current Status**: V2.7 (97.25% test coverage, Production-Ready)  
**Target Status**: V2.8 (Full async + passwordless auth)

---

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Feature 1: Celery Integration](#feature-1-celery-integration)
3. [Feature 2: User Registration API](#feature-2-user-registration-api)
4. [Feature 3: Email OTP Login](#feature-3-email-otp-login)
5. [Feature 4: Email Verification](#feature-4-email-verification)
6. [Integration Points](#integration-points)
7. [Testing Strategy](#testing-strategy)
8. [Deployment Guide](#deployment-guide)

---

## Architecture Overview

### Current State (V2.7)
```
Frontend → Django REST API → Database
                ↓
           JWT Auth (Password)
           MFA (TOTP Optional)
```

### Target State (V2.8)
```
Frontend → Django REST API → Database
    ↓           ↓              ↑
  Email    Celery Worker   Email Queue
   OTP    (Async Tasks)    (Redis)
    ↓           ↓
   Auth    Email Sending
         Verification
```

---

## Feature 1: Celery Integration

### 📊 **What We're Building**

Asynchronous task processing for:
- ✅ Email sending (verification, OTP, notifications)
- ✅ Background data processing
- ✅ Scheduled tasks (bill reminders, goal tracking)
- ✅ Report generation

### 🔧 **Technology Stack**

- **Celery 5.4+** - Task queue
- **Redis** - Message broker (already installed)
- **django-celery-beat** - Periodic tasks
- **django-celery-results** - Task result storage

### 📝 **Implementation Steps**

#### Step 1: Install Dependencies (5 min)

```bash
pip install celery==5.4.0
pip install django-celery-beat==2.7.0
pip install django-celery-results==2.6.0
pip freeze > requirements.txt
```

#### Step 2: Create Celery Configuration (10 min)

**File: `config/celery.py`**
```python
"""
Celery Configuration for KinWise Backend
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

app = Celery('kinwise')

# Load settings from Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# Periodic tasks configuration
app.conf.beat_schedule = {
    'send-bill-reminders-daily': {
        'task': 'apps.bills.tasks.send_bill_reminders',
        'schedule': crontab(hour=9, minute=0),  # 9 AM daily
    },
    'check-goal-milestones-daily': {
        'task': 'apps.goals.tasks.check_goal_milestones',
        'schedule': crontab(hour=10, minute=0),  # 10 AM daily
    },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery"""
    print(f'Request: {self.request!r}')
```

**File: `config/__init__.py`** (add to existing)
```python
# Ensure Celery app is imported when Django starts
from .celery import app as celery_app

__all__ = ('celery_app',)
```

#### Step 3: Add Celery Settings (10 min)

**File: `config/settings/base.py`** (add to end)
```python
# ==============================================================================
# CELERY CONFIGURATION
# ==============================================================================

# Broker settings (Redis)
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

# Task settings
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes max
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes soft limit

# Result backend settings
CELERY_RESULT_EXPIRES = 3600  # Results expire after 1 hour
CELERY_RESULT_PERSISTENT = True

# Worker settings
CELERY_WORKER_PREFETCH_MULTIPLIER = 4
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# Beat schedule (django-celery-beat)
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Task routes (organize by app)
CELERY_TASK_ROUTES = {
    'apps.users.tasks.*': {'queue': 'users'},
    'apps.notifications.tasks.*': {'queue': 'notifications'},
    'apps.bills.tasks.*': {'queue': 'bills'},
    'apps.goals.tasks.*': {'queue': 'goals'},
}

# Installed apps
INSTALLED_APPS += [
    'django_celery_beat',
    'django_celery_results',
]
```

#### Step 4: Create Email Tasks (15 min)

**File: `apps/users/tasks.py`** (create new)
```python
"""
User-related Celery Tasks
"""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags


@shared_task(bind=True, max_retries=3)
def send_verification_email(self, user_id: int, verification_token: str):
    """
    Send email verification link to user
    
    Args:
        user_id: User ID
        verification_token: Verification token
    """
    from apps.users.models import User
    
    try:
        user = User.objects.get(id=user_id)
        
        # Build verification URL
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
        
        # Render email template
        context = {
            'user': user,
            'verification_url': verification_url,
        }
        html_message = render_to_string('emails/verify_email.html', context)
        plain_message = strip_tags(html_message)
        
        # Send email
        send_mail(
            subject='Verify your KinWise account',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return f"Verification email sent to {user.email}"
        
    except User.DoesNotExist:
        return f"User {user_id} not found"
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_otp_email(self, user_id: int, otp_code: str):
    """
    Send OTP code to user for passwordless login
    
    Args:
        user_id: User ID
        otp_code: 6-digit OTP code
    """
    from apps.users.models import User
    
    try:
        user = User.objects.get(id=user_id)
        
        context = {
            'user': user,
            'otp_code': otp_code,
        }
        html_message = render_to_string('emails/login_otp.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject='Your KinWise login code',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return f"OTP email sent to {user.email}"
        
    except User.DoesNotExist:
        return f"User {user_id} not found"
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))


@shared_task
def send_welcome_email(user_id: int):
    """Send welcome email to new user"""
    from apps.users.models import User
    
    try:
        user = User.objects.get(id=user_id)
        
        context = {'user': user}
        html_message = render_to_string('emails/welcome.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject='Welcome to KinWise!',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
        )
        
        return f"Welcome email sent to {user.email}"
        
    except User.DoesNotExist:
        return f"User {user_id} not found"
```

#### Step 5: Run Migrations & Start Workers (10 min)

```bash
# Run migrations for celery-beat and celery-results
python manage.py migrate

# Start Celery worker (new terminal)
celery -A config worker -l info

# Start Celery beat scheduler (new terminal)
celery -A config beat -l info

# Monitor tasks (optional)
celery -A config flower
```

### ✅ **Testing Celery**

```python
# In Django shell
python manage.py shell

>>> from apps.users.tasks import debug_task
>>> result = debug_task.delay()
>>> result.status  # Should be 'SUCCESS'
```

---

## Feature 2: User Registration API

### 📊 **What We're Building**

Frontend-ready registration endpoint with:
- ✅ Email validation
- ✅ Password strength requirements
- ✅ Automatic email verification trigger
- ✅ Rate limiting (3 registrations/hour/IP)
- ✅ Audit logging

### 📝 **Implementation**

#### Step 1: Create Registration Serializer (10 min)

**File: `apps/users/serializers.py`** (add to existing)
```python
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError


class UserRegistrationSerializer(serializers.Serializer):
    """
    Serializer for user registration
    Frontend-ready with detailed validation
    """
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    first_name = serializers.CharField(required=False, max_length=150, allow_blank=True)
    last_name = serializers.CharField(required=False, max_length=150, allow_blank=True)
    
    def validate_email(self, value):
        """Validate email is unique"""
        from apps.users.models import User
        
        # Normalize email
        value = value.lower().strip()
        
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )
        
        return value
    
    def validate_password(self, value):
        """Validate password strength"""
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value
    
    def validate(self, data):
        """Validate passwords match"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                "password_confirm": "Passwords do not match."
            })
        return data
    
    def create(self, validated_data):
        """Create user and trigger verification email"""
        from apps.users.models import User, EmailVerification
        from apps.users.tasks import send_verification_email
        
        # Remove password_confirm
        validated_data.pop('password_confirm')
        
        # Create user (inactive until verified)
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            is_active=False,  # User must verify email first
        )
        
        # Create verification token
        verification = EmailVerification.objects.create(user=user)
        
        # Send verification email (async)
        send_verification_email.delay(user.id, verification.token)
        
        return user
```

#### Step 2: Create Registration View (10 min)

**File: `apps/users/views.py`** (add to existing)
```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from audit.services import log_action


class UserRegistrationView(APIView):
    """
    User registration endpoint
    Rate limited to 3 registrations per hour per IP
    """
    permission_classes = []  # Public endpoint
    
    @method_decorator(ratelimit(key='ip', rate='3/h', method='POST'))
    def post(self, request):
        """
        Register a new user
        
        Request body:
        {
            "email": "user@example.com",
            "password": "SecurePassword123!",
            "password_confirm": "SecurePassword123!",
            "first_name": "John",
            "last_name": "Doe"
        }
        """
        serializer = UserRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Log registration
            log_action(
                user=user,
                action_type='CREATE',
                action_description=f'User registered: {user.email}',
                request=request,
                object_type='User',
                object_id=user.id,
            )
            
            return Response(
                {
                    "message": "Registration successful. Please check your email to verify your account.",
                    "email": user.email,
                    "user_id": user.id,
                },
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

---

## Feature 3: Email OTP Login

### 📊 **What We're Building**

Passwordless authentication via email:
1. User enters email
2. System sends 6-digit OTP code
3. User enters code to login
4. System issues JWT token

### 📝 **Implementation**

#### Step 1: Create OTP Model (10 min)

**File: `apps/users/models.py`** (add to existing)
```python
import secrets
from django.db import models
from django.utils import timezone
from datetime import timedelta


class EmailOTP(models.Model):
    """
    One-Time Password for passwordless email login
    """
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='email_otps')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        db_table = 'email_otp'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['code', 'is_used']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.pk:
            # Generate 6-digit code
            self.code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
            # Set expiration (10 minutes)
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)
    
    def is_valid(self):
        """Check if OTP is still valid"""
        return (
            not self.is_used and
            timezone.now() < self.expires_at
        )
    
    def __str__(self):
        return f"OTP for {self.user.email} - {self.code}"
```

#### Step 2: Create OTP Views (15 min)

**File: `apps/users/views_otp.py`** (create new)
```python
"""
Email OTP (Passwordless) Authentication Views
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework_simplejwt.tokens import RefreshToken


class RequestOTPView(APIView):
    """
    Request OTP code for passwordless login
    Rate limited to 3 attempts per 10 minutes
    """
    permission_classes = []
    
    @method_decorator(ratelimit(key='ip', rate='3/10m', method='POST'))
    def post(self, request):
        """
        Request OTP code
        
        Request: {"email": "user@example.com"}
        """
        from apps.users.models import User, EmailOTP
        from apps.users.tasks import send_otp_email
        
        email = request.data.get('email', '').lower().strip()
        
        if not email:
            return Response(
                {"error": "Email is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            # Security: Don't reveal if email exists
            return Response(
                {"message": "If the email exists, an OTP code has been sent."},
                status=status.HTTP_200_OK
            )
        
        # Create OTP
        otp = EmailOTP.objects.create(
            user=user,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # Send OTP email (async)
        send_otp_email.delay(user.id, otp.code)
        
        return Response(
            {
                "message": "OTP code sent to your email",
                "expires_in": 600,  # 10 minutes
            },
            status=status.HTTP_200_OK
        )


class VerifyOTPView(APIView):
    """
    Verify OTP code and issue JWT token
    Rate limited to 5 attempts per 10 minutes
    """
    permission_classes = []
    
    @method_decorator(ratelimit(key='ip', rate='5/10m', method='POST'))
    def post(self, request):
        """
        Verify OTP and login
        
        Request: {
            "email": "user@example.com",
            "code": "123456"
        }
        """
        from apps.users.models import User, EmailOTP
        from audit.services import log_action
        
        email = request.data.get('email', '').lower().strip()
        code = request.data.get('code', '').strip()
        
        if not email or not code:
            return Response(
                {"error": "Email and code are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email, is_active=True)
            otp = EmailOTP.objects.filter(
                user=user,
                code=code,
                is_used=False
            ).order_by('-created_at').first()
            
            if not otp:
                raise EmailOTP.DoesNotExist()
            
            if not otp.is_valid():
                return Response(
                    {"error": "OTP code has expired"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Mark OTP as used
            otp.is_used = True
            otp.save()
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Log successful login
            log_action(
                user=user,
                action_type='LOGIN',
                action_description=f'User logged in via OTP: {user.email}',
                request=request,
            )
            
            return Response(
                {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                    }
                },
                status=status.HTTP_200_OK
            )
            
        except (User.DoesNotExist, EmailOTP.DoesNotExist):
            return Response(
                {"error": "Invalid email or OTP code"},
                status=status.HTTP_400_BAD_REQUEST
            )
```

---

## Feature 4: Email Verification

### 📊 **What We're Building**

Email verification system:
1. User registers
2. Receives verification email
3. Clicks link → Account activated
4. User can now login

### 📝 **Implementation**

#### Step 1: Create Email Verification Model (10 min)

**File: `apps/users/models.py`** (add to existing)
```python
import uuid
from datetime import timedelta


class EmailVerification(models.Model):
    """
    Email verification token for new user registration
    """
    user = models.OneToOneField(
        'User',
        on_delete=models.CASCADE,
        related_name='email_verification'
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'email_verification'
    
    def is_expired(self):
        """Check if verification token has expired (24 hours)"""
        return timezone.now() > self.created_at + timedelta(hours=24)
    
    def is_verified(self):
        """Check if email has been verified"""
        return self.verified_at is not None
    
    def verify(self):
        """Mark email as verified and activate user"""
        if not self.is_verified() and not self.is_expired():
            self.verified_at = timezone.now()
            self.save()
            
            # Activate user
            self.user.is_active = True
            self.user.save()
            
            return True
        return False
    
    def __str__(self):
        return f"Verification for {self.user.email}"
```

#### Step 2: Create Verification View (10 min)

**File: `apps/users/views_verification.py`** (create new)
```python
"""
Email Verification Views
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class VerifyEmailView(APIView):
    """
    Verify user email with token from email link
    """
    permission_classes = []
    
    def get(self, request):
        """
        Verify email token
        
        Query params: ?token=<uuid>
        """
        from apps.users.models import EmailVerification
        from audit.services import log_action
        
        token = request.query_params.get('token')
        
        if not token:
            return Response(
                {"error": "Verification token is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            verification = EmailVerification.objects.get(token=token)
            
            if verification.is_verified():
                return Response(
                    {"message": "Email already verified"},
                    status=status.HTTP_200_OK
                )
            
            if verification.is_expired():
                return Response(
                    {"error": "Verification token has expired"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verify email
            if verification.verify():
                # Log verification
                log_action(
                    user=verification.user,
                    action_type='EMAIL_VERIFIED',
                    action_description=f'Email verified: {verification.user.email}',
                    request=request,
                )
                
                return Response(
                    {
                        "message": "Email verified successfully",
                        "user": {
                            "email": verification.user.email,
                            "is_active": verification.user.is_active,
                        }
                    },
                    status=status.HTTP_200_OK
                )
            
            return Response(
                {"error": "Verification failed"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except EmailVerification.DoesNotExist:
            return Response(
                {"error": "Invalid verification token"},
                status=status.HTTP_400_BAD_REQUEST
            )


class ResendVerificationView(APIView):
    """
    Resend verification email
    """
    permission_classes = []
    
    def post(self, request):
        """
        Resend verification email
        
        Request: {"email": "user@example.com"}
        """
        from apps.users.models import User, EmailVerification
        from apps.users.tasks import send_verification_email
        
        email = request.data.get('email', '').lower().strip()
        
        if not email:
            return Response(
                {"error": "Email is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email)
            
            if user.is_active:
                return Response(
                    {"message": "Email already verified"},
                    status=status.HTTP_200_OK
                )
            
            # Get or create verification
            verification, created = EmailVerification.objects.get_or_create(user=user)
            
            if not created and not verification.is_expired():
                # Reuse existing token
                pass
            else:
                # Create new token
                verification.delete()
                verification = EmailVerification.objects.create(user=user)
            
            # Send verification email (async)
            send_verification_email.delay(user.id, str(verification.token))
            
            return Response(
                {"message": "Verification email sent"},
                status=status.HTTP_200_OK
            )
            
        except User.DoesNotExist:
            # Security: Don't reveal if email exists
            return Response(
                {"message": "If the email exists, a verification email has been sent."},
                status=status.HTTP_200_OK
            )
```

---

## Integration Points

### URL Configuration

**File: `config/api_v1_urls.py`** (add to existing)
```python
from apps.users.views import UserRegistrationView
from apps.users.views_otp import RequestOTPView, VerifyOTPView
from apps.users.views_verification import VerifyEmailView, ResendVerificationView

urlpatterns = [
    # ... existing patterns ...
    
    # Registration
    path('auth/register/', UserRegistrationView.as_view(), name='register'),
    
    # Email verification
    path('auth/verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('auth/resend-verification/', ResendVerificationView.as_view(), name='resend-verification'),
    
    # OTP Login
    path('auth/otp/request/', RequestOTPView.as_view(), name='request-otp'),
    path('auth/otp/verify/', VerifyOTPView.as_view(), name='verify-otp'),
]
```

### Email Templates

Create email templates directory: `templates/emails/`

**File: `templates/emails/verify_email.html`**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Verify Your Email</title>
</head>
<body>
    <h1>Welcome to KinWise, {{ user.first_name|default:user.email }}!</h1>
    <p>Please verify your email address by clicking the link below:</p>
    <p><a href="{{ verification_url }}">Verify Email</a></p>
    <p>Or copy this link: {{ verification_url }}</p>
    <p>This link will expire in 24 hours.</p>
</body>
</html>
```

**File: `templates/emails/login_otp.html`**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Your Login Code</title>
</head>
<body>
    <h1>Your KinWise Login Code</h1>
    <p>Hi {{ user.first_name|default:user.email }},</p>
    <p>Your one-time login code is:</p>
    <h2 style="font-size: 32px; letter-spacing: 5px;">{{ otp_code }}</h2>
    <p>This code will expire in 10 minutes.</p>
    <p>If you didn't request this code, please ignore this email.</p>
</body>
</html>
```

---

## Testing Strategy

### Unit Tests

**File: `apps/users/tests/test_registration.py`**
```python
from django.test import TestCase
from rest_framework.test import APIClient
from apps.users.models import User, EmailVerification


class RegistrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/v1/auth/register/'
    
    def test_registration_success(self):
        """Test successful user registration"""
        data = {
            'email': 'test@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
            'first_name': 'Test',
            'last_name': 'User',
        }
        
        response = self.client.post(self.register_url, data)
        
        self.assertEqual(response.status_code, 201)
        self.assertIn('message', response.data)
        
        # Check user created but inactive
        user = User.objects.get(email='test@example.com')
        self.assertFalse(user.is_active)
        
        # Check verification token created
        self.assertTrue(EmailVerification.objects.filter(user=user).exists())
    
    def test_registration_duplicate_email(self):
        """Test registration with existing email fails"""
        User.objects.create_user(email='test@example.com', password='pass')
        
        data = {
            'email': 'test@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
        }
        
        response = self.client.post(self.register_url, data)
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.data)
```

### Integration Tests

Test the full flow:
1. Registration → Email verification → Login
2. OTP Request → OTP Verify → JWT issued

---

## Deployment Guide

### Environment Variables

Add to `.env`:
```bash
# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@kinwise.app

# Frontend URL (for verification links)
FRONTEND_URL=http://localhost:3000
```

### Docker Compose

Add Celery services:
```yaml
services:
  celery_worker:
    build: .
    command: celery -A config worker -l info
    depends_on:
      - redis
      - db
    env_file:
      - .env
  
  celery_beat:
    build: .
    command: celery -A config beat -l info
    depends_on:
      - redis
      - db
    env_file:
      - .env
```

### Production Checklist

- [ ] Redis running and accessible
- [ ] Celery worker running
- [ ] Celery beat running
- [ ] Email backend configured
- [ ] Frontend URL set correctly
- [ ] Rate limiting tested
- [ ] Email templates created
- [ ] Migrations applied
- [ ] Tests passing

---

## Summary

### Files Created/Modified

**New Files:**
- `config/celery.py`
- `apps/users/tasks.py`
- `apps/users/views_otp.py`
- `apps/users/views_verification.py`
- `apps/users/tests/test_registration.py`
- `templates/emails/verify_email.html`
- `templates/emails/login_otp.html`
- `templates/emails/welcome.html`

**Modified Files:**
- `config/__init__.py`
- `config/settings/base.py`
- `apps/users/models.py`
- `apps/users/serializers.py`
- `apps/users/views.py`
- `config/api_v1_urls.py`
- `requirements.txt`

### API Endpoints Added

```
POST /api/v1/auth/register/           - User registration
GET  /api/v1/auth/verify-email/       - Email verification
POST /api/v1/auth/resend-verification/ - Resend verification
POST /api/v1/auth/otp/request/        - Request OTP code
POST /api/v1/auth/otp/verify/         - Verify OTP & login
```

### Time Estimate

- Celery setup: 40 minutes
- Registration API: 30 minutes
- Email OTP: 45 minutes
- Email Verification: 35 minutes
- Testing: 60 minutes
- **Total: ~4 hours**

---

**Ready to implement? Let's start with Feature 1: Celery Integration!**

Which feature would you like to start with, or should we go in order? 🚀
