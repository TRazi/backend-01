# V2.8 Quick Start Guide

## Running Celery (Development)

### Option 1: Without Redis (Testing Only)
For quick testing without installing Redis, tasks will execute synchronously:

```powershell
# Django development server
python manage.py runserver
```

### Option 2: With Redis (Recommended)

**1. Install Redis:**
- Windows: Download from https://github.com/microsoftarchive/redis/releases
- Linux: `sudo apt install redis-server`
- macOS: `brew install redis`

**2. Start Redis:**
```powershell
redis-server
```

**3. Start Celery Worker:**
```powershell
celery -A config worker -l info
```

**4. Start Celery Beat (Optional - for periodic tasks):**
```powershell
celery -A config beat -l info
```

**5. Start Django:**
```powershell
python manage.py runserver
```

## Testing the APIs

### 1. User Registration

```bash
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "SecurePassword123!",
    "password_confirm": "SecurePassword123!",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

**Expected Response:**
```json
{
  "message": "Registration successful. Please check your email to verify your account.",
  "email": "newuser@example.com",
  "user_id": 1
}
```

**Check Console:** You should see the verification email printed (console backend).

### 2. Email Verification

From the console email, copy the token and:

```bash
curl http://localhost:8000/api/v1/auth/verify-email/?token=YOUR_TOKEN_HERE
```

**Expected Response:**
```json
{
  "message": "Email verified successfully",
  "user": {
    "email": "newuser@example.com",
    "is_active": true
  }
}
```

### 3. Request OTP

```bash
curl -X POST http://localhost:8000/api/v1/auth/otp/request/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com"
  }'
```

**Expected Response:**
```json
{
  "message": "OTP code sent to your email",
  "expires_in": 600
}
```

**Check Console:** You should see the OTP email with 6-digit code.

### 4. Verify OTP

```bash
curl -X POST http://localhost:8000/api/v1/auth/otp/verify/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "code": "123456"
  }'
```

**Expected Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "email": "newuser@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "parent"
  }
}
```

## Testing with Python

```python
python manage.py shell

# Test Registration
from users.serializers import UserRegistrationSerializer
data = {
    'email': 'test@example.com',
    'password': 'SecurePassword123!',
    'password_confirm': 'SecurePassword123!',
    'first_name': 'Test'
}
ser = UserRegistrationSerializer(data=data)
ser.is_valid()  # True
user = ser.save()

# Test OTP
from users.models import EmailOTP
otp = EmailOTP.objects.create(user=user)
print(f"OTP Code: {otp.code}")
print(f"Valid: {otp.is_valid()}")

# Test Email Verification
from users.models import EmailVerification
ver = EmailVerification.objects.create(user=user)
print(f"Token: {ver.token}")
ver.verify()  # Returns True
user.refresh_from_db()
print(f"Active: {user.is_active}, Verified: {user.email_verified}")
```

## Admin Interface

Access at: http://localhost:8000/admin/

**New Admin Sections:**
- **Users → Email OTPs** - View and monitor OTP codes
  - Status badges (VALID, USED, EXPIRED)
  - Time until expiry tracking
  - IP address logging
  
- **Users → Email Verifications** - View email verification tokens
  - Status badges (VERIFIED, EXPIRED, PENDING)
  - Token preview for security
  - Time since creation tracking

- **Django Celery Beat → Periodic Tasks** - Manage scheduled tasks
- **Django Celery Results → Task Results** - View task execution history

## Troubleshooting

### Issue: Tasks not executing
**Solution:** Make sure Celery worker is running:
```powershell
celery -A config worker -l info
```

### Issue: Emails not sending
**Solution:** Check console output (development uses console backend):
```python
# In settings, verify:
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

### Issue: OTP invalid
**Cause:** OTP expires after 10 minutes
**Solution:** Request new OTP code

### Issue: Verification token expired
**Cause:** Token expires after 24 hours
**Solution:** Use resend verification endpoint:
```bash
curl -X POST http://localhost:8000/api/v1/auth/resend-verification/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
```

### Issue: Password too short
**Cause:** Minimum password length is 12 characters
**Solution:** Use password with at least 12 characters

### Issue: Rate limited
**Cause:** Too many requests
**Limits:**
- Registration: 3 per hour per IP
- OTP request: 3 per 10 minutes
- OTP verify: 5 per 10 minutes

**Solution:** Wait for rate limit to reset

## Environment Variables

Create `.env` file:

```bash
# Development
DEBUG=True
SECRET_KEY=your-secret-key

# Database (default: SQLite)
DATABASE_URL=sqlite:///db.sqlite3

# Celery (optional for development)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Email (development uses console)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Frontend
FRONTEND_URL=http://localhost:3000
```

## Production Checklist

- [ ] Install and configure Redis
- [ ] Set up email SMTP server
- [ ] Configure environment variables
- [ ] Start Celery worker as service
- [ ] Start Celery beat as service (for periodic tasks)
- [ ] Set up Celery monitoring (e.g., Flower)
- [ ] Configure email templates with branding
- [ ] Test full registration and OTP flows
- [ ] Set up logging and error tracking
- [ ] Configure rate limiting for production loads

## Monitoring Commands

```powershell
# Check Celery workers
celery -A config inspect active

# View scheduled tasks
celery -A config inspect scheduled

# View worker stats
celery -A config inspect stats

# Purge all tasks (CAREFUL!)
celery -A config purge
```

## Useful Django Commands

```powershell
# Create superuser
python manage.py createsuperuser

# Run tests
python manage.py test apps.users

# Check for issues
python manage.py check

# Shell
python manage.py shell

# Migrations
python manage.py makemigrations
python manage.py migrate
```

## API Endpoints Reference

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | /api/v1/auth/register/ | Register new user | No |
| GET | /api/v1/auth/verify-email/ | Verify email token | No |
| POST | /api/v1/auth/resend-verification/ | Resend verification | No |
| POST | /api/v1/auth/otp/request/ | Request OTP code | No |
| POST | /api/v1/auth/otp/verify/ | Verify OTP code | No |
| POST | /api/v1/auth/token/ | Login (username/password) | No |
| POST | /api/v1/auth/token/refresh/ | Refresh JWT token | No |
