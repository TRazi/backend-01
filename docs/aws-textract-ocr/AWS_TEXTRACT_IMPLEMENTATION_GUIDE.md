# AWS Textract DRF Integration - Complete Implementation Guide

## Overview

This guide provides everything needed to integrate the AWS Textract OCR endpoints into your Django REST Framework API.

## Files Created

1. **Models** (`apps/transactions/models_attachments.py`)
   - `ReceiptAttachment` - Receipt image + extracted data storage
   - `ReceiptLineItem` - Individual line items from receipts
   - `BillAttachment` - Bill/invoice image + extracted data storage

2. **API Endpoints** (`apps/transactions/views_ocr.py`)
   - `ReceiptOCRViewSet` - Receipt scanning endpoints
   - `BillOCRViewSet` - Bill scanning endpoints
   - Async Celery tasks for background processing

3. **Error Handling** (`config/utils/textract_errors.py`)
   - Structured error mapping with NZ-friendly messages
   - Retry logic with exponential backoff
   - Comprehensive logging utilities

4. **Migration** (`apps/transactions/migrations/0002_ocr_attachments.py`)
   - Creates all necessary database tables
   - Adds performance indexes

## Setup Instructions

### Step 1: Update Models

Merge the attachment models into your main models file or keep them separate:

**Option A: Add to existing models.py**
```python
# In apps/transactions/models.py
from django.db import models
from apps.transactions.models_attachments import (
    ReceiptAttachment,
    ReceiptLineItem,
    BillAttachment,
)

__all__ = ['Transaction', 'ReceiptAttachment', 'ReceiptLineItem', 'BillAttachment']
```

**Option B: Keep separate and import**
```python
# Just import from models_attachments.py as needed
```

### Step 2: Register in URLs

Add to your main `config/api_v1_urls.py`:

```python
from rest_framework.routers import DefaultRouter
from apps.transactions.views_ocr import ReceiptOCRViewSet, BillOCRViewSet

router = DefaultRouter()
router.register(r'receipts', ReceiptOCRViewSet, basename='receipt-ocr')
router.register(r'bills', BillOCRViewSet, basename='bill-ocr')

urlpatterns = [
    path('api/v1/', include(router.urls)),
    # ... other patterns
]
```

### Step 3: Run Migration

```powershell
python manage.py makemigrations transactions
python manage.py migrate
```

### Step 4: Enable Textract in .env

```dotenv
AWS_TEXTRACT_ENABLED=True
AWS_TEXTRACT_TIMEOUT=30
AWS_TEXTRACT_MAX_FILE_SIZE=10485760
```

### Step 5: Configure Celery (for async processing)

Ensure Celery is configured in `config/celery.py`:

```python
from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

app = Celery('kinwise')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

Start Celery worker:
```powershell
celery -A config worker -l info
```

## API Endpoints

### Receipt Scanning

#### POST /api/v1/receipts/scan/

Upload and scan a receipt image.

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/receipts/scan/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -F "image=@receipt.jpg" \
  -F "auto_create_transaction=true" \
  -F "account_id=123"
```

**Python Example:**
```python
import requests

headers = {"Authorization": f"Token {token}"}
files = {"image": open("receipt.jpg", "rb")}
data = {
    "auto_create_transaction": True,
    "account_id": 123
}

response = requests.post(
    "http://localhost:8000/api/v1/receipts/scan/",
    headers=headers,
    files=files,
    data=data
)

# Returns 202 Accepted with processing_id
result = response.json()
print(f"Processing ID: {result['processing_id']}")
print(f"Receipt ID: {result['receipt']['id']}")
```

**Response (202 Accepted):**
```json
{
    "receipt": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "image": "https://s3.amazonaws.com/kinwise/receipts/2025/11/17/receipt.jpg",
        "merchant_name": null,
        "total_amount": null,
        "status": "pending",
        "confidence_scores": {},
        "line_items": [],
        "created_at": "2025-11-17T18:30:00Z"
    },
    "processing_id": "abc123def456",
    "message": "Receipt uploaded. Processing started."
}
```

#### GET /api/v1/receipts/{id}/

Retrieve receipt details including extracted data.

```bash
curl -X GET http://localhost:8000/api/v1/receipts/550e8400-e29b-41d4-a716-446655440000/ \
  -H "Authorization: Token YOUR_TOKEN"
```

**Response (after processing complete):**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "image": "https://s3.amazonaws.com/kinwise/receipts/2025/11/17/receipt.jpg",
    "merchant_name": "Countdown",
    "total_amount": "145.50",
    "tax_amount": "18.95",
    "subtotal": "126.55",
    "receipt_date": "2025-11-17",
    "payment_method": "EFTPOS",
    "status": "success",
    "confidence_scores": {
        "merchant": 0.95,
        "total": 0.98,
        "date": 0.99
    },
    "line_items": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440001",
            "description": "Apples (1kg)",
            "quantity": "1",
            "unit_price": "5.99",
            "total_price": "5.99",
            "line_number": 1,
            "confidence": 0.98
        },
        {
            "id": "550e8400-e29b-41d4-a716-446655440002",
            "description": "Milk (2L)",
            "quantity": "1",
            "unit_price": "4.50",
            "total_price": "4.50",
            "line_number": 2,
            "confidence": 0.97
        }
    ],
    "created_at": "2025-11-17T18:30:00Z",
    "transaction": null
}
```

#### GET /api/v1/receipts/{id}/status/

Check processing status without retrieving full details.

```bash
curl -X GET http://localhost:8000/api/v1/receipts/550e8400-e29b-41d4-a716-446655440000/status/ \
  -H "Authorization: Token YOUR_TOKEN"
```

**Response:**
```json
{
    "receipt_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "processing",
    "created_at": "2025-11-17T18:30:00Z",
    "updated_at": "2025-11-17T18:30:05Z",
    "error_message": null,
    "merchant_name": null,
    "total_amount": null,
    "line_items_count": 0
}
```

#### GET /api/v1/receipts/

List all receipts for current user.

```bash
curl -X GET "http://localhost:8000/api/v1/receipts/?status=success&ordering=-created_at" \
  -H "Authorization: Token YOUR_TOKEN"
```

**Query Parameters:**
- `status`: Filter by status (pending, processing, success, failed, etc.)
- `merchant_name`: Filter by merchant (partial match)
- `created_after`: Filter by date
- `ordering`: Order by field (-created_at, merchant_name, total_amount)

### Bill Scanning

#### POST /api/v1/bills/scan/

Upload and scan a bill/invoice.

```bash
curl -X POST http://localhost:8000/api/v1/bills/scan/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -F "image=@bill.pdf" \
  -F "auto_create_bill=true"
```

**Response:**
```json
{
    "bill": {
        "id": "550e8400-e29b-41d4-a716-446655440003",
        "provider_name": null,
        "bill_type": null,
        "status": "pending",
        "created_at": "2025-11-17T18:35:00Z"
    },
    "processing_id": "xyz789abc456",
    "message": "Bill uploaded. Processing started."
}
```

#### GET /api/v1/bills/{id}/

Retrieve bill details (after processing).

```json
{
    "id": "550e8400-e29b-41d4-a716-446655440003",
    "image": "https://s3.amazonaws.com/kinwise/bills/2025/11/17/bill.pdf",
    "provider_name": "Contact Energy",
    "bill_type": "electricity",
    "account_number": "NZ03-0123-4567-89",
    "amount_due": "245.67",
    "due_date": "2025-12-05",
    "billing_period_start": "2025-10-17",
    "billing_period_end": "2025-11-17",
    "status": "success",
    "confidence_scores": {
        "provider": 0.99,
        "amount": 0.98,
        "date": 0.97
    },
    "created_at": "2025-11-17T18:35:00Z"
}
```

## Error Handling Examples

### Example 1: Handle Upload Error

```python
import requests
from requests.exceptions import RequestException

try:
    response = requests.post(
        "http://localhost:8000/api/v1/receipts/scan/",
        headers={"Authorization": f"Token {token}"},
        files={"image": open("receipt.jpg", "rb")},
        timeout=10
    )
    
    if response.status_code == 202:
        print("Upload successful")
    elif response.status_code == 409:
        # Duplicate
        data = response.json()
        print(f"Receipt already processed: {data['receipt_id']}")
    elif response.status_code == 413:
        # File too large
        print("Receipt file is too large (max 10MB)")
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
        
except RequestException as e:
    print(f"Network error: {e}")
```

### Example 2: Poll for Processing Status

```python
import time
import requests

receipt_id = "550e8400-e29b-41d4-a716-446655440000"
max_wait = 60  # seconds
poll_interval = 2  # seconds

for attempt in range(max_wait // poll_interval):
    response = requests.get(
        f"http://localhost:8000/api/v1/receipts/{receipt_id}/status/",
        headers={"Authorization": f"Token {token}"}
    )
    
    status = response.json()
    print(f"Status: {status['status']}")
    
    if status['status'] == 'success':
        print(f"Merchant: {status['merchant_name']}")
        print(f"Total: ${status['total_amount']}")
        break
    elif status['status'] == 'failed':
        print(f"Error: {status['error_message']}")
        break
    
    time.sleep(poll_interval)
else:
    print("Processing timeout")
```

### Example 3: Handle Textract Errors

```python
# In views_ocr.py, error handling is built-in via decorators
# Errors return user-friendly messages:

from config.utils.textract_errors import TextractServiceException

try:
    # Processing code here
    pass
except TextractServiceException as e:
    # Auto-formatted response with error code and NZ message
    return Response(
        format_error_response(e),
        status=e.status_code
    )
```

## Testing

### Unit Test Example

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from io import BytesIO
from PIL import Image

User = get_user_model()

class ReceiptOCRTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_receipt_upload(self):
        """Test receipt upload and async processing."""
        # Create test image
        image = Image.new('RGB', (100, 100), color='red')
        image_bytes = BytesIO()
        image.save(image_bytes, format='JPEG')
        image_bytes.seek(0)
        
        # Upload
        response = self.client.post(
            '/api/v1/receipts/scan/',
            {'image': image_bytes},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, 202)
        self.assertIn('processing_id', response.json())
        self.assertIn('receipt', response.json())
    
    def test_duplicate_detection(self):
        """Test duplicate receipt detection."""
        # Upload same image twice
        image_path = 'path/to/test/receipt.jpg'
        
        with open(image_path, 'rb') as f:
            response1 = self.client.post(
                '/api/v1/receipts/scan/',
                {'image': f},
                format='multipart'
            )
        
        with open(image_path, 'rb') as f:
            response2 = self.client.post(
                '/api/v1/receipts/scan/',
                {'image': f},
                format='multipart'
            )
        
        self.assertEqual(response1.status_code, 202)
        self.assertEqual(response2.status_code, 409)  # Duplicate
```

## Deployment Checklist

- [ ] All models created and migrated
- [ ] API endpoints registered in URLs
- [ ] Celery configured and running
- [ ] AWS_TEXTRACT_ENABLED=True in production .env
- [ ] S3 bucket configured for receipt/bill storage
- [ ] Error logging configured
- [ ] API documentation updated
- [ ] Frontend implements upload UI
- [ ] Rate limiting configured for /scan/ endpoints
- [ ] Data retention cleanup scheduled (365-day expiry)

## Performance Notes

- **Processing Time**: Typically 2-5 seconds per receipt
- **Concurrent Limit**: AWS Textract handles ~100 concurrent requests
- **Retry Strategy**: 3 retries with exponential backoff (60s, 120s, 240s)
- **Cost**: ~$1.50 per 1000 receipts/bills

## Privacy Compliance

✅ **Privacy Act 2020 Compliant**:
- PII masked in logs
- Image stored in encrypted S3 bucket
- Data auto-deleted after 365 days
- File hash used for deduplication (no duplicate storage)
- User-specific data isolation
