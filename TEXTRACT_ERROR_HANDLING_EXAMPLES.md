# AWS Textract Error Handling - Code Examples

## Quick Reference Examples

### Example 1: Basic Error Handling in Celery Task

```python
# In views_ocr.py - Updated process_receipt_async
from config.utils.textract_errors import (
    TextractException,
    TextractLogger,
    map_aws_error,
)
import time

@shared_task(bind=True, max_retries=3)
def process_receipt_async(self, receipt_id: str):
    """Process receipt with comprehensive error handling."""
    receipt = ReceiptAttachment.objects.get(id=receipt_id)
    start_time = time.time()
    
    try:
        receipt.status = "processing"
        receipt.save(update_fields=["status"])
        
        TextractLogger.log_processing_start(
            attachment_id=str(receipt_id),
            attachment_type="receipt",
            file_size=receipt.file_size,
        )
        
        image_bytes = receipt.image.read()
        textract = get_textract_service()
        
        if not textract.is_enabled():
            raise TextractException(
                error_code=TextractErrorCode.SERVICE_DISABLED,
                message="AWS Textract is not enabled"
            )
        
        result = textract.extract_receipt_data(image_bytes)
        
        if result["success"]:
            receipt.merchant_name = result.get("merchant_name")
            receipt.total_amount = result.get("total_amount")
            receipt.tax_amount = result.get("tax_amount")
            receipt.subtotal = result.get("subtotal")
            receipt.receipt_date = result.get("date")
            receipt.payment_method = result.get("payment_method")
            receipt.confidence_scores = result.get("confidence_scores", {})
            receipt.extracted_data = result
            receipt.merchant_normalized = result.get("merchant_normalized", False)
            receipt.status = "success"
            receipt.error_message = None
            receipt.error_code = None
            
            receipt.save()
            
            # Log success
            processing_time = time.time() - start_time
            TextractLogger.log_processing_success(
                attachment_id=str(receipt_id),
                attachment_type="receipt",
                merchant_or_provider=receipt.merchant_name,
                confidence_scores=receipt.confidence_scores,
                processing_time=processing_time,
            )
        else:
            # Extraction failed - mark as partial
            receipt.status = "partial"
            receipt.error_message = result.get("error")
            receipt.error_code = "TEXTRACT_EXTRACTION_FAILED"
            receipt.save()
            
            TextractLogger.log_processing_error(
                attachment_id=str(receipt_id),
                attachment_type="receipt",
                error_code=TextractErrorCode.INVALID_DOCUMENT,
                error_message=result.get("error"),
            )
    
    except ReceiptAttachment.DoesNotExist:
        logger.error(f"Receipt {receipt_id} not found")
    
    except TextractException as e:
        # Handle Textract-specific errors
        receipt.status = "failed"
        receipt.error_message = e.message
        receipt.error_code = e.error_code.value
        receipt.save()
        
        TextractLogger.log_processing_error(
            attachment_id=str(receipt_id),
            attachment_type="receipt",
            error_code=e.error_code,
            error_message=e.message,
            exc=e,
        )
        
        # Retry if retryable
        if _is_retryable_error(e.error_code):
            TextractLogger.log_retry(
                attachment_id=str(receipt_id),
                attempt=self.request.retries + 1,
                max_retries=self.max_retries,
                error_code=e.error_code,
            )
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    
    except Exception as e:
        # Handle unexpected errors
        receipt.status = "failed"
        receipt.error_message = str(e)
        receipt.error_code = "UNKNOWN_ERROR"
        receipt.save()
        
        TextractLogger.log_processing_error(
            attachment_id=str(receipt_id),
            attachment_type="receipt",
            error_code=TextractErrorCode.UNKNOWN,
            error_message=str(e),
            exc=e,
        )
        
        # Retry
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
```

### Example 2: Error Handling in ViewSet

```python
# In views_ocr.py - Updated scan action
from config.utils.textract_errors import (
    format_error_response,
    TextractLogger,
)

@action(detail=False, methods=["post"], serializer_class=ReceiptUploadSerializer)
def scan(self, request):
    """Upload receipt with error handling."""
    serializer = self.get_serializer(data=request.data)
    
    try:
        serializer.is_valid(raise_exception=True)
        image_file = serializer.validated_data["image"]
        image_bytes = image_file.read()
        
        # Validate size
        max_size = settings.AWS_TEXTRACT_MAX_FILE_SIZE
        if len(image_bytes) > max_size:
            TextractLogger.log_validation_error(
                attachment_type="receipt",
                error_message=f"File size exceeds limit ({len(image_bytes)} > {max_size})",
            )
            return Response(
                {
                    "error": f"File size exceeds limit of {max_size // (1024*1024)}MB",
                },
                status=status.HTTP_413_PAYLOAD_TOO_LARGE,
            )
        
        # Calculate hash
        import hashlib
        file_hash = hashlib.sha256(image_bytes).hexdigest()
        
        # Check for duplicate
        existing = ReceiptAttachment.objects.filter(
            user=request.user,
            file_hash=file_hash
        ).first()
        
        if existing:
            TextractLogger.log_deduplication(
                user_id=str(request.user.id),
                file_hash=file_hash,
                existing_id=str(existing.id),
            )
            return Response(
                {
                    "error": "This receipt has already been processed",
                    "receipt_id": str(existing.id),
                    "created_at": existing.created_at,
                },
                status=status.HTTP_409_CONFLICT,
            )
        
        # Create and process
        receipt = ReceiptAttachment.objects.create(
            user=request.user,
            image=ContentFile(image_bytes, name=image_file.name),
            file_size=len(image_bytes),
            file_hash=file_hash,
        )
        
        TextractLogger.log_upload(
            user_id=str(request.user.id),
            file_hash=file_hash,
            file_size=len(image_bytes),
            file_type="receipt",
        )
        
        # Queue async processing
        task = process_receipt_async.delay(str(receipt.id))
        
        return Response(
            {
                "receipt": ReceiptAttachmentSerializer(receipt).data,
                "processing_id": task.id,
                "message": "Receipt uploaded. Processing started.",
            },
            status=status.HTTP_202_ACCEPTED,
        )
    
    except serializers.ValidationError as e:
        TextractLogger.log_validation_error(
            attachment_type="receipt",
            error_message=str(e.detail),
            details=e.detail,
        )
        return Response(
            format_error_response(e),
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    except Exception as e:
        logger.error(f"Error uploading receipt: {e}", exc_info=True)
        return Response(
            format_error_response(e),
            status=status.HTTP_400_BAD_REQUEST,
        )
```

### Example 3: Custom Error Handler Middleware

```python
# In config/middleware/textract_error_middleware.py
from django.utils.deprecation import MiddlewareMixin
from config.utils.textract_errors import TextractServiceException

class TextractErrorMiddleware(MiddlewareMixin):
    """Middleware to handle Textract errors globally."""
    
    def process_exception(self, request, exception):
        """Handle Textract exceptions."""
        if isinstance(exception, TextractServiceException):
            from rest_framework.response import Response
            
            return Response(
                {
                    "error": {
                        "code": exception.error_code.value,
                        "message": str(exception.detail),
                        "type": "textract_error",
                    }
                },
                status=exception.status_code,
            )
        
        return None

# Add to settings.py MIDDLEWARE list
MIDDLEWARE = [
    # ...
    'config.middleware.textract_error_middleware.TextractErrorMiddleware',
    # ...
]
```

### Example 4: Frontend Error Handling (JavaScript)

```javascript
// Frontend error handling for receipt upload

async function uploadReceipt(imageFile, autoCreateTransaction = false) {
    try {
        const formData = new FormData();
        formData.append('image', imageFile);
        formData.append('auto_create_transaction', autoCreateTransaction);
        
        const response = await fetch('/api/v1/receipts/scan/', {
            method: 'POST',
            headers: {
                'Authorization': `Token ${token}`,
            },
            body: formData,
        });
        
        // Handle different status codes
        if (response.status === 202) {
            // Accepted - processing started
            const data = await response.json();
            console.log('Processing started:', data.processing_id);
            
            // Poll for status
            return pollReceiptStatus(data.receipt.id);
        
        } else if (response.status === 409) {
            // Duplicate
            const data = await response.json();
            showError(`Receipt already processed: ${data.receipt_id}`);
            
        } else if (response.status === 413) {
            // File too large
            showError('Receipt file is too large (max 10MB)');
            
        } else if (response.status === 400) {
            // Bad request
            const data = await response.json();
            showError(data.error?.message || 'Invalid receipt format');
            
        } else if (response.status === 503) {
            // Service unavailable
            const data = await response.json();
            showError('Receipt scanning is temporarily unavailable. Please try again later.');
            
        } else {
            const data = await response.json();
            showError(data.error?.message || 'An error occurred');
        }
        
    } catch (error) {
        console.error('Upload error:', error);
        showError('Network error. Please check your connection.');
    }
}

async function pollReceiptStatus(receiptId, maxAttempts = 60) {
    let attempts = 0;
    
    while (attempts < maxAttempts) {
        try {
            const response = await fetch(`/api/v1/receipts/${receiptId}/status/`, {
                headers: {
                    'Authorization': `Token ${token}`,
                }
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                // Done!
                showSuccess(`Receipt processed: ${data.merchant_name}`);
                return data;
            
            } else if (data.status === 'failed') {
                // Failed
                showError(`Receipt processing failed: ${data.error_message}`);
                return null;
            
            } else if (data.status === 'processing') {
                // Still processing - wait and retry
                await new Promise(resolve => setTimeout(resolve, 2000));
                attempts++;
            
            } else {
                // Pending
                await new Promise(resolve => setTimeout(resolve, 1000));
                attempts++;
            }
        
        } catch (error) {
            console.error('Status check error:', error);
            break;
        }
    }
    
    showError('Receipt processing timeout');
    return null;
}
```

### Example 5: Logging Configuration

```python
# In config/settings/base.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'textract.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'config.utils.textract_errors': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.transactions.views_ocr': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

### Example 6: Metrics Dashboard Query

```python
# Query performance metrics
from config.utils.textract_errors import get_processing_metrics
from apps.transactions.models_attachments import ReceiptAttachment, BillAttachment
from django.utils import timezone
from datetime import timedelta

def get_ocr_metrics_summary():
    """Get OCR performance metrics for dashboard."""
    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    
    receipts = ReceiptAttachment.objects.filter(created_at__gte=last_24h)
    bills = BillAttachment.objects.filter(created_at__gte=last_24h)
    
    return {
        'receipts': {
            'total': receipts.count(),
            'successful': receipts.filter(status='success').count(),
            'failed': receipts.filter(status='failed').count(),
            'processing': receipts.filter(status='processing').count(),
            'avg_amount': receipts.filter(total_amount__isnull=False)
                .aggregate(Avg('total_amount'))['total_amount__avg'],
        },
        'bills': {
            'total': bills.count(),
            'successful': bills.filter(status='success').count(),
            'failed': bills.filter(status='failed').count(),
            'processing': bills.filter(status='processing').count(),
            'by_type': dict(bills.values('bill_type').annotate(count=Count('id'))),
        },
        'library_metrics': get_processing_metrics(),
    }
```

## Common Error Codes & Fixes

| Status | Error Code | Message | Fix |
|--------|-----------|---------|-----|
| 413 | DOCUMENT_TOO_LARGE | File size exceeds 10MB | Compress image or use PDF |
| 400 | VALIDATION_EXCEPTION | Receipt image format invalid | Upload JPG, PNG, or PDF |
| 400 | BAD_DOCUMENT | Receipt quality too low | Take clearer photo |
| 429 | THROTTLING_EXCEPTION | Too many requests | Automatic retry with backoff |
| 409 | DUPLICATE | Receipt already processed | Use returned existing receipt_id |
| 503 | SERVICE_UNAVAILABLE | AWS temporarily unavailable | Retry later (auto-retried) |

