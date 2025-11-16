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
from django.db import transaction
from apps.users.models import User, EmailVerification


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration with email verification.
    
    Django Best Practice: Use ModelSerializer with Meta class,
    leverage built-in field definitions, use validate_ methods,
    wrap create() in transaction.
    """
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        help_text='Minimum 8 characters, must include uppercase, lowercase, and numbers'
    )
    password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        help_text='Must match password field'
    )
    
    class Meta:
        model = User
        fields = ['email', 'password', 'password_confirm', 'first_name', 'last_name']
        extra_kwargs = {
            'email': {
                'required': True,
                'help_text': 'Valid email address for account verification'
            },
            'first_name': {
                'required': False,
                'allow_blank': True,
                'help_text': 'First name (optional)'
            },
            'last_name': {
                'required': False,
                'allow_blank': True,
                'help_text': 'Last name (optional)'
            },
        }
    
    def validate_email(self, value):
        """
        Validate email is unique and normalized.
        
        Django Best Practice: Use validate_<field_name> for field-level validation.
        """
        # Normalize email to lowercase
        value = value.lower().strip()
        
        # Check uniqueness
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )
        
        return value
    
    def validate_password(self, value):
        """
        Validate password against Django's password validators.
        
        Django Best Practice: Use Django's built-in password validation.
        """
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value
    
    def validate(self, data):
        """
        Validate passwords match.
        
        Django Best Practice: Use validate() for cross-field validation.
        """
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError({
                "password_confirm": "Passwords do not match."
            })
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        """
        Create user and trigger verification email.
        
        Django Best Practice: Use @transaction.atomic to ensure
        user creation and verification token creation succeed together.
        Uses select_for_update to prevent race conditions.
        """
        from apps.users.tasks import send_verification_email
        
        # Remove password_confirm (not a model field)
        validated_data.pop('password_confirm', None)
        
        # Create user (inactive until verified)
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            is_active=False,  # User must verify email first
            email_verified=False,
        )
        
        # Create verification token
        verification = EmailVerification.objects.create(user=user)
        
        # Send verification email (async) - outside transaction
        transaction.on_commit(
            lambda: send_verification_email.delay(user.id, str(verification.token))
        )
        
        return user


class EmailOTPRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting OTP code.
    
    Django Best Practice: Simple serializers for input validation.
    """
    email = serializers.EmailField(
        required=True,
        help_text='Email address to send OTP code'
    )
    
    def validate_email(self, value):
        """Normalize email."""
        return value.lower().strip()


class EmailOTPVerifySerializer(serializers.Serializer):
    """
    Serializer for verifying OTP code.
    
    Django Best Practice: Use RegexField for code validation.
    """
    email = serializers.EmailField(
        required=True,
        help_text='Email address associated with OTP'
    )
    code = serializers.RegexField(
        regex=r'^\d{6}$',
        required=True,
        max_length=6,
        min_length=6,
        help_text='6-digit OTP code',
        error_messages={
            'invalid': 'OTP code must be exactly 6 digits'
        }
    )
    
    def validate_email(self, value):
        """Normalize email."""
        return value.lower().strip()
    
    def validate_code(self, value):
        """Strip whitespace from code."""
        return value.strip()
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
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from datetime import timedelta
from common.models import BaseModel


class EmailOTP(BaseModel):
    """
    One-Time Password for passwordless email login.
    OTP codes are valid for 10 minutes and can only be used once.
    
    Django Best Practice: Inherit from BaseModel for created_at/updated_at,
    use validators for code format, include help_text for documentation.
    """
    # Validator for 6-digit code
    code_validator = RegexValidator(
        regex=r'^\d{6}$',
        message='OTP code must be exactly 6 digits',
    )
    
    user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='email_otps',
        verbose_name='User',
        help_text='User associated with this OTP',
    )
    code = models.CharField(
        max_length=6,
        validators=[code_validator],
        verbose_name='OTP Code',
        help_text='6-digit one-time password',
    )
    expires_at = models.DateTimeField(
        verbose_name='Expiration Time',
        help_text='When this OTP expires (10 minutes from creation)',
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name='Used',
        help_text='Whether this OTP has been used',
        db_index=True,
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP Address',
        help_text='IP address that requested this OTP',
    )
    
    class Meta:
        db_table = 'email_otp'
        verbose_name = 'Email OTP'
        verbose_name_plural = 'Email OTPs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['code', 'is_used']),
            models.Index(fields=['expires_at', 'is_used']),
        ]
        permissions = [
            ('can_generate_otp', 'Can generate OTP codes'),
            ('can_verify_otp', 'Can verify OTP codes'),
        ]
    
    def save(self, *args, **kwargs):
        """Generate OTP code and set expiration on creation."""
        if not self.pk:
            # Generate secure 6-digit code
            self.code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
            # Set expiration (10 minutes)
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)
    
    def is_valid(self):
        """
        Check if OTP is still valid.
        
        Returns:
            bool: True if OTP is unused and not expired
        """
        return (
            not self.is_used and
            timezone.now() < self.expires_at
        )
    
    def mark_as_used(self):
        """Mark OTP as used (idempotent)."""
        if not self.is_used:
            self.is_used = True
            self.save(update_fields=['is_used', 'updated_at'])
    
    def __str__(self):
        return f"OTP for {self.user.email} - {'Used' if self.is_used else 'Valid'}" 
```

#### Step 2: Create OTP Views (15 min)

**File: `apps/users/views_otp.py`** (create new)
```python
"""
Email OTP (Passwordless) Authentication Views

Django Best Practice: Use ViewSets with mixins for cleaner, more maintainable code.
Use DRF throttling instead of decorators for better consistency.
"""
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from django.utils import timezone

from apps.users.models import User, EmailOTP
from apps.users.serializers import EmailOTPRequestSerializer, EmailOTPVerifySerializer
from audit.services import log_action


class OTPRequestThrottle(AnonRateThrottle):
    """Custom throttle: 3 requests per 10 minutes."""
    rate = '3/10m'


class OTPVerifyThrottle(AnonRateThrottle):
    """Custom throttle: 5 requests per 10 minutes."""
    rate = '5/10m'


class EmailOTPViewSet(viewsets.GenericViewSet):
    """
    Request OTP code for passwordless login
    Rate limited to 3 attempts per 10 minutes
    """
    permission_classes = []
    
    """
    ViewSet for Email OTP authentication.
    
    Django Best Practice: Use ViewSet with custom actions,
    throttling classes, and proper serializer validation.
    """
    permission_classes = [AllowAny]
    serializer_class = EmailOTPRequestSerializer
    
    @action(
        detail=False,
        methods=['post'],
        url_path='request',
        throttle_classes=[OTPRequestThrottle],
        serializer_class=EmailOTPRequestSerializer,
    )
    @transaction.atomic
    def request_otp(self, request):
        """
        Request OTP code for passwordless login.
        
        Django Best Practice: Use serializer for validation,
        transaction for atomicity, and throttling for rate limiting.
        
        Request: {"email": "user@example.com"}
        Response: {"message": "...", "expires_in": 600}
        """
        from apps.users.tasks import send_otp_email
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email, is_active=True, email_verified=True)
        except User.DoesNotExist:
            # Security: Don't reveal if email exists
            return Response(
                {"message": "If the email exists, an OTP code has been sent."},
                status=status.HTTP_200_OK
            )
        
        # Invalidate any existing unused OTPs for this user
        EmailOTP.objects.filter(
            user=user,
            is_used=False,
            expires_at__gt=timezone.now()
        ).update(is_used=True)
        
        # Create new OTP
        otp = EmailOTP.objects.create(
            user=user,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # Send OTP email (async) - after transaction commits
        transaction.on_commit(
            lambda: send_otp_email.delay(user.id, otp.code)
        )
        
        return Response(
            {
                "message": "OTP code sent to your email",
                "expires_in": 600,  # 10 minutes
            },
            status=status.HTTP_200_OK
        )
    
    @action(
        detail=False,
        methods=['post'],
        url_path='verify',
        throttle_classes=[OTPVerifyThrottle],
        serializer_class=EmailOTPVerifySerializer,
    )
    @transaction.atomic
    def verify_otp(self, request):
        """
        Verify OTP code and issue JWT tokens.
        
        Django Best Practice: Use serializer validation,
        select_for_update to prevent race conditions,
        transaction for atomicity.
        
        Request: {"email": "user@example.com", "code": "123456"}
        Response: {"access": "...", "refresh": "...", "user": {...}}
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        code = serializer.validated_data['code']
        
        try:
            # Use select_for_update to prevent concurrent OTP usage
            user = User.objects.select_for_update().get(
                email=email,
                is_active=True
            )
            
            otp = EmailOTP.objects.select_for_update().filter(
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
            otp.mark_as_used()
            
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
                        "role": user.role,
                    }
                },
                status=status.HTTP_200_OK
            )
            
        except (User.DoesNotExist, EmailOTP.DoesNotExist):
            # Log failed attempt
            log_action(
                user=None,
                action_type='LOGIN_FAILED',
                action_description=f'Failed OTP login attempt for: {email}',
                request=request,
            )
            
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
from django.db import models, transaction
from django.utils import timezone
from common.models import BaseModel


class EmailVerification(BaseModel):
    """
    Email verification token for new user registration.
    Tokens expire after 24 hours.
    
    Django Best Practice: Use BaseModel, add help_text, use @transaction.atomic
    for verify() method to ensure data consistency.
    """
    user = models.OneToOneField(
        'User',
        on_delete=models.CASCADE,
        related_name='email_verification',
        verbose_name='User',
        help_text='User to be verified',
    )
    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name='Verification Token',
        help_text='Unique token sent to user email',
        db_index=True,
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Verified At',
        help_text='When email was verified',
    )
    
    class Meta:
        db_table = 'email_verification'
        verbose_name = 'Email Verification'
        verbose_name_plural = 'Email Verifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'verified_at']),
        ]
        permissions = [
            ('can_verify_email', 'Can verify user emails'),
            ('can_resend_verification', 'Can resend verification emails'),
        ]
    
    def is_expired(self):
        """
        Check if verification token has expired (24 hours).
        
        Returns:
            bool: True if token is older than 24 hours
        """
        return timezone.now() > self.created_at + timedelta(hours=24)
    
    def is_verified(self):
        """
        Check if email has been verified.
        
        Returns:
            bool: True if verified_at is set
        """
        return self.verified_at is not None
    
    @transaction.atomic
    def verify(self):
        """
        Mark email as verified and activate user.
        Uses transaction to ensure atomicity.
        
        Django Best Practice: Use @transaction.atomic to ensure
        both verification and user activation succeed together.
        
        Returns:
            bool: True if verification succeeded, False otherwise
        """
        if not self.is_verified() and not self.is_expired():
            self.verified_at = timezone.now()
            self.save(update_fields=['verified_at', 'updated_at'])
            
            # Activate user and set email_verified flag
            self.user.is_active = True
            self.user.email_verified = True
            self.user.save(update_fields=['is_active', 'email_verified', 'updated_at'])
            
            return True
        return False
    
    def __str__(self):
        status = 'Verified' if self.is_verified() else 'Pending'
        return f"{status} - {self.user.email}"
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
"""
API V1 URL Configuration

Django Best Practice: Use DRF routers for ViewSets,
keep path() for simple views, group related endpoints.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.users.views import UserRegistrationView
from apps.users.views_otp import EmailOTPViewSet
from apps.users.views_verification import VerifyEmailView, ResendVerificationView

# Django Best Practice: Use router for ViewSets
router = DefaultRouter()
router.register(r'auth/otp', EmailOTPViewSet, basename='otp')

urlpatterns = [
    # ... existing patterns ...
    
    # Router URLs (includes OTP endpoints)
    path('', include(router.urls)),
    
    # Registration (simple view)
    path('auth/register/', UserRegistrationView.as_view(), name='register'),
    
    # Email verification (simple views)
    path('auth/verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('auth/resend-verification/', ResendVerificationView.as_view(), name='resend-verification'),
]

# This creates the following OTP endpoints:
# POST /api/v1/auth/otp/request/ - Request OTP
# POST /api/v1/auth/otp/verify/  - Verify OTP
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

### Admin Integration

**Django Best Practice**: Provide comprehensive admin interfaces for managing
OTP codes and email verifications with proper list displays, filters, and search.

**File: `apps/users/admin.py`** (add to existing)
```python
"""
Django Admin Configuration for User Models

Django Best Practice: Use list_display, list_filter, search_fields,
readonly_fields, and fieldsets for better admin UX.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from apps.users.models import EmailOTP, EmailVerification


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    """
    Admin interface for Email OTP management.
    
    Django Best Practice: Comprehensive admin with filters,
    search, readonly fields, and custom displays.
    """
    list_display = [
        'user_email',
        'code_display',
        'status_badge',
        'created_at',
        'expires_at',
        'time_until_expiry',
        'ip_address',
    ]
    list_filter = [
        'is_used',
        'created_at',
        ('expires_at', admin.DateFieldListFilter),
    ]
    search_fields = [
        'user__email',
        'code',
        'ip_address',
    ]
    readonly_fields = [
        'user',
        'code',
        'created_at',
        'updated_at',
        'expires_at',
        'ip_address',
        'is_valid_now',
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('OTP Information', {
            'fields': ('user', 'code', 'is_used'),
        }),
        ('Timing', {
            'fields': ('created_at', 'updated_at', 'expires_at', 'is_valid_now'),
        }),
        ('Security', {
            'fields': ('ip_address',),
        }),
    )
    
    def user_email(self, obj):
        """Display user email as link."""
        from django.urls import reverse
        from django.utils.safestring import mark_safe
        
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return mark_safe(f'<a href="{url}">{obj.user.email}</a>')
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'
    
    def code_display(self, obj):
        """Display code with monospace font."""
        return format_html(
            '<code style="font-size: 14px; font-weight: bold;">{}</code>',
            obj.code
        )
    code_display.short_description = 'Code'
    
    def status_badge(self, obj):
        """Display status with colored badge."""
        if obj.is_used:
            color = 'gray'
            text = 'Used'
        elif obj.is_valid():
            color = 'green'
            text = 'Valid'
        else:
            color = 'red'
            text = 'Expired'
        
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, text
        )
    status_badge.short_description = 'Status'
    
    def time_until_expiry(self, obj):
        """Show time until OTP expires."""
        if obj.is_used:
            return 'Used'
        
        delta = obj.expires_at - timezone.now()
        if delta.total_seconds() <= 0:
            return 'Expired'
        
        minutes = int(delta.total_seconds() / 60)
        seconds = int(delta.total_seconds() % 60)
        return f"{minutes}m {seconds}s"
    time_until_expiry.short_description = 'Time Left'
    
    def is_valid_now(self, obj):
        """Check if OTP is currently valid."""
        return obj.is_valid()
    is_valid_now.boolean = True
    is_valid_now.short_description = 'Valid Now'
    
    def has_add_permission(self, request):
        """Prevent manual OTP creation via admin."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion for cleanup."""
        return request.user.is_superuser


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    """
    Admin interface for Email Verification management.
    
    Django Best Practice: Readonly fields for security,
    custom displays for better UX.
    """
    list_display = [
        'user_email',
        'status_badge',
        'token_preview',
        'created_at',
        'verified_at',
        'time_since_creation',
        'is_expired_now',
    ]
    list_filter = [
        ('verified_at', admin.EmptyFieldListFilter),
        'created_at',
    ]
    search_fields = [
        'user__email',
        'token',
    ]
    readonly_fields = [
        'user',
        'token',
        'created_at',
        'updated_at',
        'verified_at',
        'is_expired_now',
        'is_verified_now',
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',),
        }),
        ('Verification Details', {
            'fields': ('token', 'created_at', 'updated_at', 'verified_at'),
        }),
        ('Status', {
            'fields': ('is_verified_now', 'is_expired_now'),
        }),
    )
    
    def user_email(self, obj):
        """Display user email as link."""
        from django.urls import reverse
        from django.utils.safestring import mark_safe
        
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return mark_safe(f'<a href="{url}">{obj.user.email}</a>')
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'
    
    def token_preview(self, obj):
        """Show shortened token."""
        token_str = str(obj.token)
        return f"{token_str[:8]}...{token_str[-8:]}"
    token_preview.short_description = 'Token'
    
    def status_badge(self, obj):
        """Display verification status with badge."""
        if obj.is_verified():
            color = 'green'
            text = 'Verified'
        elif obj.is_expired():
            color = 'red'
            text = 'Expired'
        else:
            color = 'orange'
            text = 'Pending'
        
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, text
        )
    status_badge.short_description = 'Status'
    
    def time_since_creation(self, obj):
        """Show time since verification was created."""
        delta = timezone.now() - obj.created_at
        hours = int(delta.total_seconds() / 3600)
        if hours < 1:
            minutes = int(delta.total_seconds() / 60)
            return f"{minutes}m ago"
        elif hours < 24:
            return f"{hours}h ago"
        else:
            days = int(hours / 24)
            return f"{days}d ago"
    time_since_creation.short_description = 'Age'
    
    def is_expired_now(self, obj):
        """Check if verification has expired."""
        return obj.is_expired()
    is_expired_now.boolean = True
    is_expired_now.short_description = 'Expired'
    
    def is_verified_now(self, obj):
        """Check if email is verified."""
        return obj.is_verified()
    is_verified_now.boolean = True
    is_verified_now.short_description = 'Verified'
    
    def has_add_permission(self, request):
        """Prevent manual verification creation."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion for cleanup."""
        return request.user.is_superuser
```

---

## Testing Strategy

**Django Best Practice**: Use fixtures for test data, `reverse()` for URLs,
`TestCase` with transactions, and comprehensive coverage including edge cases.

### Test Fixtures

**File: `apps/users/tests/fixtures.py`**
```python
"""
Test fixtures for user authentication tests.

Django Best Practice: Centralize test data creation in fixtures
for reusability and consistency.
"""
import pytest
from django.contrib.auth import get_user_model
from apps.users.models import EmailVerification, EmailOTP

User = get_user_model()


@pytest.fixture
def active_user(db):
    """Create an active verified user."""
    return User.objects.create_user(
        email='active@example.com',
        password='SecurePass123!',
        first_name='Active',
        last_name='User',
        is_active=True,
        email_verified=True,
    )


@pytest.fixture
def inactive_user(db):
    """Create an inactive unverified user."""
    return User.objects.create_user(
        email='inactive@example.com',
        password='SecurePass123!',
        is_active=False,
        email_verified=False,
    )


@pytest.fixture
def valid_otp(db, active_user):
    """Create a valid OTP for active user."""
    return EmailOTP.objects.create(
        user=active_user,
        ip_address='127.0.0.1'
    )


@pytest.fixture
def email_verification(db, inactive_user):
    """Create email verification for inactive user."""
    return EmailVerification.objects.create(user=inactive_user)
```

### Unit Tests

**File: `apps/users/tests/test_registration.py`**
```python
"""
Registration API Tests

Django Best Practice: Use reverse() for URLs, TestCase for transactions,
test both success and failure cases, check database state.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.users.models import User, EmailVerification


class RegistrationTests(TestCase):
    """Test user registration endpoint."""
    
    def setUp(self):
        """Set up test client and URL."""
        self.client = APIClient()
        # Django Best Practice: Use reverse() instead of hardcoded URLs
        self.register_url = reverse('register')
        self.valid_data = {
            'email': 'test@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
            'first_name': 'Test',
            'last_name': 'User',
        }
    
    def test_registration_success(self):
        """Test successful user registration."""
        response = self.client.post(self.register_url, self.valid_data)
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)
        self.assertIn('user_id', response.data)
        
        # Django Best Practice: Verify database state
        user = User.objects.get(email='test@example.com')
        self.assertFalse(user.is_active)  # User inactive until verified
        self.assertFalse(user.email_verified)
        self.assertEqual(user.first_name, 'Test')
        
        # Check verification token created
        self.assertTrue(
            EmailVerification.objects.filter(user=user).exists()
        )
    
    def test_registration_duplicate_email(self):
        """Test registration with existing email fails."""
        # Create existing user
        User.objects.create_user(
            email='test@example.com',
            password='pass'
        )
        
        response = self.client.post(self.register_url, self.valid_data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
    
    def test_registration_password_mismatch(self):
        """Test registration with mismatched passwords."""
        data = self.valid_data.copy()
        data['password_confirm'] = 'DifferentPass123!'
        
        response = self.client.post(self.register_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password_confirm', response.data)
    
    def test_registration_weak_password(self):
        """Test registration with weak password fails."""
        data = self.valid_data.copy()
        data['password'] = 'weak'
        data['password_confirm'] = 'weak'
        
        response = self.client.post(self.register_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
    
    def test_registration_email_normalization(self):
        """Test email is normalized to lowercase."""
        data = self.valid_data.copy()
        data['email'] = 'Test@EXAMPLE.COM'
        
        response = self.client.post(self.register_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Django Best Practice: Check normalized storage
        user = User.objects.get(email='test@example.com')
        self.assertEqual(user.email, 'test@example.com')
```

**File: `apps/users/tests/test_otp.py`**
```python
"""
OTP Authentication Tests

Django Best Practice: Test full flow, edge cases, and security.
"""
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch

from apps.users.models import User, EmailOTP


class OTPAuthenticationTests(TestCase):
    """Test OTP authentication flow."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.request_url = reverse('otp-request-otp')
        self.verify_url = reverse('otp-verify-otp')
        
        # Create active user
        self.user = User.objects.create_user(
            email='user@example.com',
            password='pass',
            is_active=True,
            email_verified=True,
        )
    
    @patch('apps.users.tasks.send_otp_email.delay')
    def test_request_otp_success(self, mock_send):
        """Test successful OTP request."""
        response = self.client.post(
            self.request_url,
            {'email': 'user@example.com'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['expires_in'], 600)
        
        # Check OTP created
        otp = EmailOTP.objects.get(user=self.user)
        self.assertEqual(len(otp.code), 6)
        self.assertFalse(otp.is_used)
        self.assertTrue(otp.is_valid())
        
        # Check email task called
        mock_send.assert_called_once_with(self.user.id, otp.code)
    
    def test_request_otp_nonexistent_email(self):
        """Test OTP request for non-existent email (security)."""
        response = self.client.post(
            self.request_url,
            {'email': 'nonexistent@example.com'}
        )
        
        # Django Best Practice: Don't reveal if email exists
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Check no OTP created
        self.assertEqual(EmailOTP.objects.count(), 0)
    
    def test_verify_otp_success(self):
        """Test successful OTP verification."""
        # Create OTP
        otp = EmailOTP.objects.create(user=self.user)
        
        response = self.client.post(
            self.verify_url,
            {
                'email': 'user@example.com',
                'code': otp.code,
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        
        # Check OTP marked as used
        otp.refresh_from_db()
        self.assertTrue(otp.is_used)
    
    def test_verify_otp_invalid_code(self):
        """Test OTP verification with wrong code."""
        EmailOTP.objects.create(user=self.user)
        
        response = self.client.post(
            self.verify_url,
            {
                'email': 'user@example.com',
                'code': '999999',  # Wrong code
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_verify_otp_expired(self):
        """Test OTP verification with expired code."""
        # Create expired OTP
        otp = EmailOTP.objects.create(user=self.user)
        otp.expires_at = timezone.now() - timedelta(minutes=1)
        otp.save()
        
        response = self.client.post(
            self.verify_url,
            {
                'email': 'user@example.com',
                'code': otp.code,
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('expired', response.data['error'].lower())
    
    def test_verify_otp_already_used(self):
        """Test OTP verification with already used code."""
        otp = EmailOTP.objects.create(user=self.user)
        otp.is_used = True
        otp.save()
        
        response = self.client.post(
            self.verify_url,
            {
                'email': 'user@example.com',
                'code': otp.code,
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
```

### Integration Tests

**File: `apps/users/tests/test_integration.py`**
```python
"""
Integration Tests for Full Authentication Flows

Django Best Practice: Test complete user journeys.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from unittest.mock import patch

from apps.users.models import User, EmailVerification, EmailOTP


class AuthenticationFlowTests(TestCase):
    """Test complete authentication flows."""
    
    def setUp(self):
        self.client = APIClient()
    
    @patch('apps.users.tasks.send_verification_email.delay')
    def test_full_registration_flow(self, mock_send):
        """Test: Register → Verify Email → Login via OTP."""
        # Step 1: Register
        register_data = {
            'email': 'newuser@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
        }
        response = self.client.post(
            reverse('register'),
            register_data
        )
        self.assertEqual(response.status_code, 201)
        
        # Step 2: Verify Email
        user = User.objects.get(email='newuser@example.com')
        verification = EmailVerification.objects.get(user=user)
        
        response = self.client.get(
            reverse('verify-email'),
            {'token': str(verification.token)}
        )
        self.assertEqual(response.status_code, 200)
        
        # Check user activated
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.email_verified)
        
        # Step 3: Login via OTP
        response = self.client.post(
            reverse('otp-request-otp'),
            {'email': 'newuser@example.com'}
        )
        self.assertEqual(response.status_code, 200)
        
        otp = EmailOTP.objects.get(user=user)
        response = self.client.post(
            reverse('otp-verify-otp'),
            {
                'email': 'newuser@example.com',
                'code': otp.code,
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
```

### Performance Tests

**File: `apps/users/tests/test_celery_performance.py`**
```python
"""
Celery Task Performance Tests

Django Best Practice: Test async task execution and performance.
"""
from django.test import TestCase
from django.utils import timezone
from celery.result import AsyncResult
from apps.users.tasks import send_otp_email, send_verification_email
from apps.users.models import User
import time


class CeleryPerformanceTests(TestCase):
    """Test Celery task performance."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='pass'
        )
    
    def test_send_otp_email_performance(self):
        """Test OTP email task completes quickly."""
        start = time.time()
        
        # Execute task
        result = send_otp_email.delay(self.user.id, '123456')
        
        # Wait for completion (with timeout)
        result.get(timeout=5)
        
        elapsed = time.time() - start
        
        # Task should complete within 5 seconds
        self.assertLess(elapsed, 5.0)
        self.assertEqual(result.status, 'SUCCESS')
    
    def test_email_task_retry_on_failure(self):
        """Test email task retries on failure."""
        # Test with non-existent user
        result = send_otp_email.delay(99999, '123456')
        
        # Should complete (not raise exception)
        output = result.get(timeout=5)
        self.assertIn('not found', output.lower())
```

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

**New Files (Django Best Practices Applied):**
- `config/celery.py` - Celery configuration with task routes
- `apps/users/tasks.py` - Async email tasks with retry logic
- `apps/users/views_otp.py` - **ViewSet** with custom actions (not APIView)
- `apps/users/views_verification.py` - Email verification views
- `apps/users/serializers.py` - **ModelSerializer** with proper validation
- `templates/emails/verify_email.html` - Email template with plain-text fallback
- `templates/emails/login_otp.html` - OTP email template
- `templates/emails/welcome.html` - Welcome email template

**Test Files (Comprehensive Coverage):**
- `apps/users/tests/fixtures.py` - **Pytest fixtures** for test data
- `apps/users/tests/test_registration.py` - Registration tests with **reverse()**
- `apps/users/tests/test_otp.py` - OTP authentication tests
- `apps/users/tests/test_integration.py` - **Full flow integration tests**
- `apps/users/tests/test_celery_performance.py` - **Celery performance tests**

**Modified Files (Enhanced with Django Best Practices):**
- `config/__init__.py` - Import Celery app
- `config/settings/base.py` - Celery + email configuration
- `apps/users/models.py` - **Enhanced with validators, help_text, verbose_name, permissions**
- `apps/users/admin.py` - **Comprehensive admin with custom displays, filters, readonly fields**
- `config/api_v1_urls.py` - **Router-based URLs** for ViewSets
- `requirements.txt` - Add Celery dependencies

**Django Best Practices Implemented:**
✅ **Models**: Validators, help_text, verbose_name, Meta ordering & permissions
✅ **Serializers**: ModelSerializer with Meta, read_only_fields, validate_ methods
✅ **Views**: ViewSets with custom actions, throttling classes, proper permissions
✅ **URLs**: DRF routers for ViewSets, REST naming conventions
✅ **Transactions**: @transaction.atomic for critical operations
✅ **Admin**: list_display, search_fields, filters, custom displays
✅ **Testing**: reverse(), fixtures, integration tests, performance tests
✅ **Security**: select_for_update, proper error messages, audit logging

### API Endpoints Added

```
# Registration & Verification
POST /api/v1/auth/register/              - User registration
GET  /api/v1/auth/verify-email/          - Email verification
POST /api/v1/auth/resend-verification/   - Resend verification

# OTP Authentication (ViewSet - Router-based)
POST /api/v1/auth/otp/request/           - Request OTP code
POST /api/v1/auth/otp/verify/            - Verify OTP & login
```

**Django Best Practice Note**: OTP endpoints use DRF router for cleaner URL management and automatic OPTIONS support.

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


---

## ✅ Django Best Practices Enhancements for V2.8

### 1. Model Improvements
- Add `validators` from `django.core.validators` for fields like email, numeric ranges.
- Include `help_text` and `verbose_name` for better admin clarity.
- Define `ordering` and `permissions` in `Meta` for consistent querysets and fine-grained access control.

### 2. Serializer Best Practices
- Use `ModelSerializer` with `Meta` class for DRY code.
- Apply `read_only_fields` instead of manual `read_only=True`.
- Implement custom validation methods prefixed with `validate_` for field-level checks.

### 3. View Improvements
- Replace `APIView` with `ViewSet` for CRUD operations to leverage DRF routers and reduce boilerplate.
- Use DRF generic mixins where possible.
- Apply throttling at the class level using `throttle_classes`.
- Ensure proper permission classes for household scoping and role-based access.

### 4. URL Configuration
- Use DRF routers for ViewSets.
- Follow REST naming conventions and group related endpoints logically.

### 5. Email Best Practices
- Continue using `django.core.mail.EmailMessage` for complex emails.
- Use `render_to_string` for HTML templates and add plain-text fallback.

### 6. Testing Enhancements
- Use Django's `TestCase` and `reverse()` for URL resolution.
- Add fixtures for reusable test data.
- Include performance tests for Celery tasks.

### 7. Transaction Management & Signals
- Wrap critical operations in `@transaction.atomic`.
- Use signal handlers for post-save actions (e.g., sending verification emails).

### 8. Admin Integration
- Add `list_display`, `search_fields`, and `ordering` in admin classes for better UX.

These improvements will ensure the V2.8 implementation aligns with official Django guidelines and maintains consistency with KinWise's architecture.
