# AWS Textract OCR - Complete Integration & Deployment Guide

**Status:** Production-Ready Implementation  
**Last Updated:** November 17, 2025  
**Target Environment:** Ubuntu 22.04 LTS / AWS EC2

---

## Table of Contents

1. [Pre-Integration Checklist](#pre-integration-checklist)
2. [Step 1: Environment Configuration](#step-1-environment-configuration)
3. [Step 2: URL Registration](#step-2-url-registration)
4. [Step 3: Database Migration](#step-3-database-migration)
5. [Step 4: Celery Configuration](#step-4-celery-configuration)
6. [Step 5: Sentry Setup](#step-5-sentry-setup)
7. [Step 6: Testing](#step-6-testing)
8. [Step 7: Monitoring & Alerts](#step-7-monitoring--alerts)
9. [Step 8: Deployment](#step-8-deployment)
10. [Troubleshooting](#troubleshooting)

---

## Pre-Integration Checklist

Before deploying, ensure:

- [ ] AWS account with Textract API access
- [ ] AWS Access Key ID and Secret Access Key
- [ ] S3 bucket for receipt/bill image storage
- [ ] PostgreSQL database configured
- [ ] Redis instance for Celery (or RabbitMQ)
- [ ] Python 3.10+ and Django 4.2+
- [ ] Celery installed and configured
- [ ] (Optional) Sentry account for error tracking

### Required AWS Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "textract:AnalyzeDocument",
        "textract:StartDocumentAnalysis",
        "textract:GetDocumentAnalysis"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::kinwise-receipts/*"
    }
  ]
}
```

---

## Step 1: Environment Configuration

### 1.1 Update `.env` file

```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=ap-southeast-2

# Textract Configuration
AWS_TEXTRACT_ENABLED=True
AWS_TEXTRACT_TIMEOUT=30
AWS_TEXTRACT_MAX_FILE_SIZE=10485760  # 10MB in bytes
AWS_TEXTRACT_MAX_RETRIES=3

# S3 Configuration
USE_S3=True
AWS_STORAGE_BUCKET_NAME=kinwise-receipts
AWS_S3_CUSTOM_DOMAIN=kinwise-receipts.s3.amazonaws.com
AWS_S3_REGION_NAME=ap-southeast-2

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CELERY_TASK_TIME_LIMIT=600  # 10 minutes
CELERY_TASK_SOFT_TIME_LIMIT=480  # 8 minutes

# Sentry Configuration (Optional)
SENTRY_DSN=https://your_key@sentry.io/your_project_id
SENTRY_ENVIRONMENT=production
```

### 1.2 Verify AWS credentials

```bash
python manage.py shell
```

```python
from django.conf import settings

# Check settings
print('AWS_TEXTRACT_ENABLED:', settings.AWS_TEXTRACT_ENABLED)
print('AWS_REGION:', settings.AWS_REGION)
print('AWS_ACCESS_KEY_ID:', settings.AWS_ACCESS_KEY_ID[:10] + '...')

# Test AWS connection
import boto3
client = boto3.client(
    'textract',
    region_name=settings.AWS_REGION,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)
print('✅ AWS Textract connection successful')
```

---

## Step 2: URL Registration

### 2.1 Update `config/api_v1_urls.py`

```python
# config/api_v1_urls.py
from rest_framework.routers import DefaultRouter
from apps.transactions.views_ocr import ReceiptOCRViewSet, BillOCRViewSet

# Create router
router = DefaultRouter()

# Register OCR endpoints
router.register(
    r'receipts',
    ReceiptOCRViewSet,
    basename='receipt-ocr'
)
router.register(
    r'bills',
    BillOCRViewSet,
    basename='bill-ocr'
)

# Include in urlpatterns
urlpatterns = [
    # ... existing patterns ...
] + router.urls
```

### 2.2 Verify URLs

```bash
python manage.py show_urls | grep -E 'receipts|bills'
```

Expected output:
```
/api/v1/receipts/                     ReceiptOCRViewSet
/api/v1/receipts/<uuid:pk>/           ReceiptOCRViewSet
/api/v1/receipts/<uuid:pk>/status/    ReceiptOCRViewSet
/api/v1/receipts/scan/                ReceiptOCRViewSet
/api/v1/bills/                        BillOCRViewSet
/api/v1/bills/<uuid:pk>/              BillOCRViewSet
/api/v1/bills/<uuid:pk>/status/       BillOCRViewSet
/api/v1/bills/scan/                   BillOCRViewSet
```

---

## Step 3: Database Migration

### 3.1 Create and run migration

```bash
# Check pending migrations
python manage.py showmigrations transactions

# Run migration
python manage.py migrate transactions

# Verify tables created
python manage.py dbshell
```

```sql
-- Check tables
\dt transactions_*

-- Expected tables:
-- transactions_receiptattachment
-- transactions_receiptlineitem
-- transactions_billattachment

-- Check indexes
\d transactions_receiptattachment
```

### 3.2 Create superuser for admin

```bash
python manage.py createsuperuser
```

### 3.3 Access Django admin

Visit `http://localhost:8000/admin/transactions/` to verify models.

---

## Step 4: Celery Configuration

### 4.1 Verify Celery setup

```python
# config/celery.py
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

app = Celery('kinwise')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Add periodic tasks for cleanup
app.conf.beat_schedule = {
    'cleanup-expired-receipts': {
        'task': 'apps.transactions.tasks.cleanup_expired_receipts',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'cleanup-expired-bills': {
        'task': 'apps.transactions.tasks.cleanup_expired_bills',
        'schedule': crontab(hour=2, minute=30),  # Daily at 2:30 AM
    },
}
```

### 4.2 Create cleanup tasks

```python
# apps/transactions/tasks.py
from celery import shared_task
from django.utils import timezone
from apps.transactions.models_attachments import ReceiptAttachment, BillAttachment
import logging

logger = logging.getLogger(__name__)

@shared_task
def cleanup_expired_receipts():
    """Delete expired receipt attachments (older than 365 days)."""
    now = timezone.now()
    expired = ReceiptAttachment.objects.filter(expires_at__lte=now)
    count = expired.count()
    
    if count > 0:
        expired.delete()
        logger.info(f"Cleaned up {count} expired receipts")
    
    return {'deleted': count}


@shared_task
def cleanup_expired_bills():
    """Delete expired bill attachments (older than 365 days)."""
    now = timezone.now()
    expired = BillAttachment.objects.filter(expires_at__lte=now)
    count = expired.count()
    
    if count > 0:
        expired.delete()
        logger.info(f"Cleaned up {count} expired bills")
    
    return {'deleted': count}
```

### 4.3 Start Celery worker

```bash
# Terminal 1: Start Celery worker
celery -A config worker -l info

# Terminal 2: Start Celery beat (for periodic tasks)
celery -A config beat -l info

# Production: Use supervisor or systemd
# See systemd service files below
```

### 4.4 Systemd service files (Production)

**File: `/etc/systemd/system/celery-worker.service`**
```ini
[Unit]
Description=Celery Service
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/var/www/kinwise/backend

Environment="PATH=/var/www/kinwise/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=config.settings.production"
ExecStart=/var/www/kinwise/venv/bin/celery -A config worker --loglevel=info --pidfile=/var/run/celery/worker.pid --logfile=/var/log/celery/worker.log

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**File: `/etc/systemd/system/celery-beat.service`**
```ini
[Unit]
Description=Celery Beat Service
After=network.target redis.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/kinwise/backend

Environment="PATH=/var/www/kinwise/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=config.settings.production"
ExecStart=/var/www/kinwise/venv/bin/celery -A config beat --loglevel=info

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable services:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable celery-worker celery-beat
sudo systemctl start celery-worker celery-beat
sudo systemctl status celery-worker celery-beat
```

---

## Step 5: Sentry Setup

### 5.1 Create Sentry account

1. Go to https://sentry.io/
2. Create free account
3. Create new project (select Django)
4. Copy DSN URL

### 5.2 Install Sentry SDK

```bash
pip install sentry-sdk
```

### 5.3 Configure in Django settings

```python
# config/settings/production.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

sentry_sdk.init(
    dsn=os.getenv('SENTRY_DSN'),
    integrations=[
        DjangoIntegration(),
        CeleryIntegration(),
    ],
    traces_sample_rate=0.1,
    send_default_pii=False,
    environment=os.getenv('SENTRY_ENVIRONMENT', 'production'),
)
```

### 5.4 Test Sentry integration

```bash
python manage.py shell
```

```python
import sentry_sdk

# Send test message
sentry_sdk.capture_message("Test message from KinWise")

# Or test error
try:
    1 / 0
except Exception as e:
    sentry_sdk.capture_exception(e)

print("✅ Sentry test event sent. Check your Sentry dashboard.")
```

---

## Step 6: Testing

### 6.1 Unit tests

```bash
# Run all OCR tests
python manage.py test apps.transactions.tests.test_ocr

# Run specific test
python manage.py test apps.transactions.tests.test_ocr.ReceiptOCRViewSetTest.test_upload_receipt

# With coverage
coverage run --source='apps.transactions' manage.py test
coverage report
```

### 6.2 Integration test

```python
# apps/transactions/tests/test_ocr_integration.py
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.utils import override_settings
import os

User = get_user_model()

@override_settings(AWS_TEXTRACT_ENABLED=True)
class ReceiptOCRIntegrationTest(TestCase):
    """Integration tests for receipt OCR."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_full_receipt_workflow(self):
        """Test complete receipt upload and processing workflow."""
        # 1. Upload receipt
        test_image_path = 'path/to/test_receipt.jpg'
        with open(test_image_path, 'rb') as img:
            response = self.client.post(
                '/api/v1/receipts/scan/',
                {'image': img},
                format='multipart'
            )
        
        self.assertEqual(response.status_code, 202)
        receipt_id = response.data['receipt']['id']
        
        # 2. Check status (may be processing)
        response = self.client.get(f'/api/v1/receipts/{receipt_id}/status/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(response.data['status'], ['processing', 'success'])
        
        # 3. Wait for processing
        import time
        time.sleep(5)
        
        # 4. Get details
        response = self.client.get(f'/api/v1/receipts/{receipt_id}/')
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data['merchant_name'])
        
        print("✅ Full workflow test passed")
```

### 6.3 Manual API testing

```bash
# Create test token
python manage.py drf_create_token testuser

# Upload receipt
curl -X POST http://localhost:8000/api/v1/receipts/scan/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -F "image=@path/to/receipt.jpg"

# Expected response (202 Accepted):
{
  "receipt": {
    "id": "uuid",
    "status": "pending"
  },
  "processing_id": "celery-task-id",
  "message": "Receipt uploaded. Processing started."
}

# Check status
curl -X GET http://localhost:8000/api/v1/receipts/UUID/status/ \
  -H "Authorization: Token YOUR_TOKEN"

# Get details
curl -X GET http://localhost:8000/api/v1/receipts/UUID/ \
  -H "Authorization: Token YOUR_TOKEN"
```

---

## Step 7: Monitoring & Alerts

### 7.1 Set up health check endpoint

```python
# config/urls.py
from config.utils.textract_monitoring import get_ocr_health_status
from django.http import JsonResponse

def health_check(request):
    """Health check endpoint for OCR system."""
    health = get_ocr_health_status()
    status_code = 200 if health['status'] == 'healthy' else 503
    return JsonResponse(health, status=status_code)

urlpatterns = [
    # ...
    path('health/ocr/', health_check),
]
```

### 7.2 Set up Sentry alerts

In Sentry dashboard:

1. Go to Alerts
2. Create new alert rule:
   - **Condition:** Error event
   - **Filter:** `environment:production`
   - **Action:** Send email notification

3. Create threshold alert:
   - **Condition:** Error rate exceeds 10% in 5 minutes
   - **Action:** Send email + Slack notification

### 7.3 Configure Slack notifications (Optional)

```python
# In Sentry project settings:
# Integrations → Slack → Authorize
# Then configure alerts to send to #ocr-errors channel
```

---

## Step 8: Deployment

### 8.1 Pre-deployment checklist

```bash
# 1. Run all tests
python manage.py test

# 2. Check code quality
flake8 apps/transactions config/utils
black --check apps/transactions config/utils

# 3. Verify all migrations are applied
python manage.py migrate --dry-run

# 4. Collect static files
python manage.py collectstatic --noinput

# 5. Create backup
pg_dump kinwise_db > backup_20251117.sql

# 6. Test on staging
# Deploy to staging environment and run full test suite
```

### 8.2 Deployment steps

```bash
# 1. Pull latest code
git pull origin main

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run migrations
python manage.py migrate

# 4. Restart services
sudo systemctl restart gunicorn
sudo systemctl restart celery-worker
sudo systemctl restart celery-beat

# 5. Verify deployment
curl https://api.kinwise.nz/health/ocr/

# 6. Monitor Sentry
# Check Sentry dashboard for any new errors
```

### 8.3 Rollback procedure

```bash
# If issues occur:
git revert <commit-hash>
git push origin main

python manage.py migrate transactions 0001_initial

sudo systemctl restart gunicorn celery-worker celery-beat

# Restore from backup if needed
psql kinwise_db < backup_20251117.sql
```

---

## Troubleshooting

### Common Issues

#### 1. AWS Textract Connection Error

**Error:** `botocore.exceptions.ClientError: An error occurred (AccessDenied)`

**Solution:**
```bash
# Check credentials
python manage.py shell

from django.conf import settings
import boto3

client = boto3.client(
    'textract',
    region_name=settings.AWS_REGION,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)

# Test connection
response = client.list_operations()
print(response)
```

#### 2. Celery Tasks Not Processing

**Error:** Tasks stuck in "pending" status

**Solution:**
```bash
# Check Celery worker is running
celery -A config inspect active

# If not running, start worker
celery -A config worker -l info

# Check Redis connection
redis-cli ping
# Should return: PONG

# Check Celery configuration
python manage.py shell
from config import celery_app
print(celery_app.conf)
```

#### 3. File Too Large Error

**Error:** `DocumentTooLarge` from AWS Textract

**Solution:**
```bash
# Check file size limit in .env
AWS_TEXTRACT_MAX_FILE_SIZE=10485760  # 10MB

# Compress image before uploading
# Max supported by AWS: 10MB (300 DPI)
# Recommend: < 5MB for faster processing
```

#### 4. Duplicate Receipt Detection Not Working

**Error:** Duplicate receipts being processed

**Solution:**
```bash
# Check file hash is being calculated
python manage.py shell

from apps.transactions.models_attachments import ReceiptAttachment
import hashlib

# Verify hash calculation
receipt = ReceiptAttachment.objects.first()
if not receipt.file_hash:
    # Regenerate hash
    image_bytes = receipt.image.read()
    receipt.file_hash = hashlib.sha256(image_bytes).hexdigest()
    receipt.save()
```

#### 5. S3 Permission Denied

**Error:** `botocore.exceptions.ClientError: (403) Forbidden`

**Solution:**
```bash
# Verify S3 bucket policy allows writing
aws s3 ls s3://kinwise-receipts/

# Check IAM permissions
# Ensure user has:
# - s3:GetObject
# - s3:PutObject
# - s3:DeleteObject
```

### Debug Logging

Enable verbose logging to troubleshoot:

```python
# config/settings/development.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'apps.transactions': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'config.utils': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

Then run:
```bash
python manage.py runserver --verbosity 3
```

---

## Performance Optimization

### 1. Database Queries

```python
# Use select_related for ForeignKey
receipts = ReceiptAttachment.objects.select_related('user').all()

# Use prefetch_related for reverse relations
receipts = ReceiptAttachment.objects.prefetch_related('line_items').all()

# Use only() to fetch specific fields
receipts = ReceiptAttachment.objects.only('id', 'merchant_name', 'status')
```

### 2. Celery Task Optimization

```python
# Increase concurrency for high volume
celery -A config worker -c 10  # 10 concurrent tasks

# Set task time limits
@shared_task(time_limit=600, soft_time_limit=480)
def process_receipt_async(receipt_id):
    # Task will be killed after 600s, warned at 480s
    pass
```

### 3. Caching

```python
from django.core.cache import cache

# Cache receipt details
def get_receipt_with_cache(receipt_id):
    cache_key = f'receipt:{receipt_id}'
    receipt = cache.get(cache_key)
    
    if not receipt:
        receipt = ReceiptAttachment.objects.get(id=receipt_id)
        cache.set(cache_key, receipt, timeout=3600)  # 1 hour
    
    return receipt
```

---

## Success Criteria

✅ All tests passing  
✅ AWS Textract connection successful  
✅ Celery tasks processing receipts/bills  
✅ Database migrations applied  
✅ S3 storage working  
✅ Sentry receiving errors  
✅ API endpoints responding correctly  
✅ No errors in production logs  
✅ Performance metrics within acceptable range  

---

**Support & Documentation:**

- AWS Textract docs: https://docs.aws.amazon.com/textract/
- Celery docs: https://docs.celeryproject.io/
- Sentry docs: https://docs.sentry.io/
- Django REST Framework: https://www.django-rest-framework.org/

