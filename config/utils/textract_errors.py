"""
Error Handling and Logging Utilities for AWS Textract Integration

Provides comprehensive error handling, retry logic, and structured logging
for OCR operations with NZ-specific error messages.
"""

import logging
import traceback
from typing import Dict, Any, Optional, Callable
from functools import wraps
from enum import Enum

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import APIException

logger = logging.getLogger(__name__)


# ============================================================================
# Error Types
# ============================================================================


class TextractErrorCode(Enum):
    """AWS Textract error codes with NZ-friendly messages."""
    
    # Service errors
    THROTTLING_EXCEPTION = "ThrottlingException"
    PROVISIONED_THROUGHPUT_EXCEEDED = "ProvisionedThroughputExceededException"
    VALIDATION_EXCEPTION = "ValidationException"
    INTERNAL_SERVER_ERROR = "InternalServerError"
    SERVICE_UNAVAILABLE = "ServiceUnavailable"
    
    # Document errors
    INVALID_DOCUMENT = "InvalidDocument"
    DOCUMENT_TOO_LARGE = "DocumentTooLarge"
    UNSUPPORTED_DOCUMENT = "UnsupportedDocument"
    BAD_DOCUMENT = "BadDocument"
    
    # Configuration errors
    ACCESS_DENIED = "AccessDeniedException"
    INVALID_PARAMETER = "InvalidParameterException"
    
    # Custom errors
    SERVICE_DISABLED = "SERVICE_DISABLED"
    TIMEOUT = "TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"
    UNKNOWN = "UNKNOWN"


class TextractException(Exception):
    """Base exception for Textract operations."""
    
    def __init__(
        self,
        error_code: TextractErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class TextractServiceException(APIException):
    """Exception raised by Textract service."""
    
    status_code = 503
    default_detail = _("AWS Textract service is temporarily unavailable")
    
    def __init__(
        self,
        error_code: TextractErrorCode,
        message: Optional[str] = None
    ):
        self.error_code = error_code
        self.detail = message or self._get_user_friendly_message(error_code)
        super().__init__(detail=self.detail)

    @staticmethod
    def _get_user_friendly_message(error_code: TextractErrorCode) -> str:
        """Convert error code to user-friendly NZ message."""
        messages = {
            TextractErrorCode.THROTTLING_EXCEPTION: 
                _("Receipt processing is busy. Please try again in a few moments."),
            TextractErrorCode.PROVISIONED_THROUGHPUT_EXCEEDED: 
                _("Too many receipts being processed. Please try again soon."),
            TextractErrorCode.VALIDATION_EXCEPTION: 
                _("Receipt image format is not supported. Please try JPG, PNG or PDF."),
            TextractErrorCode.INVALID_DOCUMENT: 
                _("The receipt image could not be read. Please try a clearer photo."),
            TextractErrorCode.DOCUMENT_TOO_LARGE: 
                _("Receipt file is too large (max 10MB). Please try a smaller image."),
            TextractErrorCode.UNSUPPORTED_DOCUMENT: 
                _("Document type is not supported. Please upload a receipt or bill."),
            TextractErrorCode.BAD_DOCUMENT: 
                _("Receipt image quality is too low. Please try a clearer photo."),
            TextractErrorCode.ACCESS_DENIED: 
                _("AWS credentials are invalid. Contact support."),
            TextractErrorCode.INTERNAL_SERVER_ERROR: 
                _("AWS is experiencing issues. Please try again later."),
            TextractErrorCode.SERVICE_UNAVAILABLE: 
                _("AWS Textract service is unavailable. Please try again later."),
            TextractErrorCode.SERVICE_DISABLED: 
                _("Receipt scanning is currently disabled. Please try again later."),
            TextractErrorCode.TIMEOUT: 
                _("Receipt processing took too long. Please try a smaller image."),
            TextractErrorCode.NETWORK_ERROR: 
                _("Network connection error. Please check your internet and try again."),
            TextractErrorCode.UNKNOWN: 
                _("An unexpected error occurred. Please try again."),
        }
        
        return str(messages.get(error_code, messages[TextractErrorCode.UNKNOWN]))


# ============================================================================
# Error Mapping
# ============================================================================


ERROR_MAPPING = {
    # AWS Textract exceptions
    "ThrottlingException": (TextractErrorCode.THROTTLING_EXCEPTION, 429),
    "ProvisionedThroughputExceededException": (
        TextractErrorCode.PROVISIONED_THROUGHPUT_EXCEEDED,
        429,
    ),
    "ValidationException": (TextractErrorCode.VALIDATION_EXCEPTION, 400),
    "InvalidParameterException": (TextractErrorCode.INVALID_PARAMETER, 400),
    "InvalidDocument": (TextractErrorCode.INVALID_DOCUMENT, 400),
    "DocumentTooLarge": (TextractErrorCode.DOCUMENT_TOO_LARGE, 413),
    "UnsupportedDocument": (TextractErrorCode.UNSUPPORTED_DOCUMENT, 415),
    "BadDocument": (TextractErrorCode.BAD_DOCUMENT, 400),
    "AccessDeniedException": (TextractErrorCode.ACCESS_DENIED, 403),
    "InternalServerError": (TextractErrorCode.INTERNAL_SERVER_ERROR, 503),
    "ServiceUnavailable": (TextractErrorCode.SERVICE_UNAVAILABLE, 503),
}


# ============================================================================
# Logging Utilities
# ============================================================================


class TextractLogger:
    """Structured logging for Textract operations."""
    
    @staticmethod
    def log_upload(
        user_id: str,
        file_hash: str,
        file_size: int,
        file_type: str,
    ) -> None:
        """Log receipt/bill upload."""
        logger.info(
            "OCR upload started",
            extra={
                "user_id": user_id,
                "file_hash": file_hash[:8],  # Only log first 8 chars
                "file_size": file_size,
                "file_type": file_type,
                "event": "ocr_upload_started",
            }
        )

    @staticmethod
    def log_processing_start(
        attachment_id: str,
        attachment_type: str,
        file_size: int,
    ) -> None:
        """Log start of Textract processing."""
        logger.info(
            "OCR processing started",
            extra={
                "attachment_id": attachment_id,
                "attachment_type": attachment_type,
                "file_size": file_size,
                "event": "ocr_processing_started",
            }
        )

    @staticmethod
    def log_processing_success(
        attachment_id: str,
        attachment_type: str,
        merchant_or_provider: Optional[str],
        confidence_scores: Dict[str, float],
        processing_time: float,
    ) -> None:
        """Log successful Textract processing."""
        logger.info(
            "OCR processing completed successfully",
            extra={
                "attachment_id": attachment_id,
                "attachment_type": attachment_type,
                "merchant_or_provider": merchant_or_provider,
                "avg_confidence": sum(confidence_scores.values()) / len(confidence_scores)
                if confidence_scores
                else 0,
                "processing_time_seconds": processing_time,
                "event": "ocr_processing_success",
            }
        )

    @staticmethod
    def log_processing_error(
        attachment_id: str,
        attachment_type: str,
        error_code: TextractErrorCode,
        error_message: str,
        exc: Optional[Exception] = None,
    ) -> None:
        """Log Textract processing error."""
        logger.error(
            "OCR processing failed",
            extra={
                "attachment_id": attachment_id,
                "attachment_type": attachment_type,
                "error_code": error_code.value,
                "error_message": error_message,
                "event": "ocr_processing_error",
            },
            exc_info=exc,
        )

    @staticmethod
    def log_retry(
        attachment_id: str,
        attempt: int,
        max_retries: int,
        error_code: TextractErrorCode,
    ) -> None:
        """Log retry attempt."""
        logger.warning(
            f"OCR processing retry: attempt {attempt}/{max_retries}",
            extra={
                "attachment_id": attachment_id,
                "attempt": attempt,
                "max_retries": max_retries,
                "error_code": error_code.value,
                "event": "ocr_retry",
            }
        )

    @staticmethod
    def log_deduplication(
        user_id: str,
        file_hash: str,
        existing_id: str,
    ) -> None:
        """Log duplicate file detection."""
        logger.info(
            "Duplicate receipt/bill detected",
            extra={
                "user_id": user_id,
                "file_hash": file_hash[:8],
                "existing_id": existing_id,
                "event": "ocr_duplicate_detected",
            }
        )

    @staticmethod
    def log_validation_error(
        attachment_type: str,
        error_message: str,
        details: Optional[Dict] = None,
    ) -> None:
        """Log validation error."""
        logger.warning(
            f"OCR validation error: {error_message}",
            extra={
                "attachment_type": attachment_type,
                "error_message": error_message,
                "details": details,
                "event": "ocr_validation_error",
            }
        )


# ============================================================================
# Decorators
# ============================================================================


def textract_error_handler(
    operation_name: str,
    max_retries: int = 3,
    backoff_factor: float = 2.0,
):
    """
    Decorator to handle Textract errors with retry logic.
    
    Args:
        operation_name: Name of the operation being performed
        max_retries: Maximum number of retry attempts
        backoff_factor: Exponential backoff multiplier
    """
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            attempt = 0
            last_error = None
            
            while attempt <= max_retries:
                try:
                    return func(*args, **kwargs)
                    
                except TextractException as e:
                    last_error = e
                    
                    # Don't retry non-retryable errors
                    if not _is_retryable_error(e.error_code):
                        logger.error(
                            f"{operation_name} failed (non-retryable): {e.error_code.value}",
                            extra={"error": str(e)}
                        )
                        raise TextractServiceException(e.error_code) from e
                    
                    # Log retry
                    if attempt < max_retries:
                        TextractLogger.log_retry(
                            attachment_id=kwargs.get("attachment_id", "unknown"),
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            error_code=e.error_code,
                        )
                        attempt += 1
                    else:
                        logger.error(
                            f"{operation_name} failed after {max_retries} retries",
                            extra={"error": str(e)}
                        )
                        raise TextractServiceException(e.error_code) from e
                        
                except Exception as e:
                    logger.error(
                        f"{operation_name} failed with unexpected error",
                        extra={"error": str(e)},
                        exc_info=True
                    )
                    raise TextractServiceException(TextractErrorCode.UNKNOWN) from e
            
            return None
        
        return wrapper
    
    return decorator


def validate_textract_enabled(func: Callable) -> Callable:
    """Decorator to check if Textract is enabled before operation."""
    
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        from config.utils.ocr_service import get_textract_service
        
        textract = get_textract_service()
        
        if not textract.is_enabled():
            TextractLogger.log_validation_error(
                attachment_type=kwargs.get("attachment_type", "unknown"),
                error_message="Textract service is disabled",
            )
            raise TextractServiceException(TextractErrorCode.SERVICE_DISABLED)
        
        return func(*args, **kwargs)
    
    return wrapper


# ============================================================================
# Helper Functions
# ============================================================================


def _is_retryable_error(error_code: TextractErrorCode) -> bool:
    """Determine if an error should trigger a retry."""
    retryable = [
        TextractErrorCode.THROTTLING_EXCEPTION,
        TextractErrorCode.PROVISIONED_THROUGHPUT_EXCEEDED,
        TextractErrorCode.INTERNAL_SERVER_ERROR,
        TextractErrorCode.SERVICE_UNAVAILABLE,
        TextractErrorCode.TIMEOUT,
        TextractErrorCode.NETWORK_ERROR,
    ]
    return error_code in retryable


def map_aws_error(error: Exception) -> TextractException:
    """
    Map AWS SDK exceptions to TextractException.
    
    Args:
        error: AWS SDK exception
        
    Returns:
        TextractException with mapped error code
    """
    error_type = type(error).__name__
    error_response = getattr(error, "response", {})
    error_code_from_aws = error_response.get("Error", {}).get("Code", error_type)
    
    # Try to map to known error code
    if error_code_from_aws in ERROR_MAPPING:
        mapped_code, _ = ERROR_MAPPING[error_code_from_aws]
        return TextractException(
            error_code=mapped_code,
            message=str(error),
            details={"aws_error_code": error_code_from_aws}
        )
    
    # Default to unknown
    return TextractException(
        error_code=TextractErrorCode.UNKNOWN,
        message=str(error),
        details={"aws_error_code": error_code_from_aws}
    )


def format_error_response(exc: Exception) -> Dict[str, Any]:
    """
    Format exception as JSON-serializable error response.
    
    Args:
        exc: Exception to format
        
    Returns:
        Dict with error details suitable for API response
    """
    if isinstance(exc, TextractServiceException):
        return {
            "error": {
                "code": exc.error_code.value,
                "message": str(exc.detail),
                "type": "textract_error",
            }
        }
    
    elif isinstance(exc, ValidationError):
        return {
            "error": {
                "code": "validation_error",
                "message": str(exc.detail) if hasattr(exc, 'detail') else str(exc),
                "type": "validation_error",
            }
        }
    
    else:
        return {
            "error": {
                "code": "unknown_error",
                "message": "An unexpected error occurred",
                "type": "unknown_error",
            }
        }


# ============================================================================
# Performance Monitoring
# ============================================================================


class ProcessingMetrics:
    """Track OCR processing metrics."""
    
    def __init__(self):
        self.successful_count = 0
        self.failed_count = 0
        self.total_processing_time = 0.0
        self.average_confidence = 0.0

    def record_success(self, processing_time: float, confidence: float) -> None:
        """Record successful processing."""
        self.successful_count += 1
        self.total_processing_time += processing_time
        self.average_confidence = (
            (self.average_confidence * (self.successful_count - 1) + confidence) /
            self.successful_count
        )

    def record_failure(self) -> None:
        """Record failed processing."""
        self.failed_count += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        total = self.successful_count + self.failed_count
        return {
            "successful": self.successful_count,
            "failed": self.failed_count,
            "total": total,
            "success_rate": (
                self.successful_count / total * 100 if total > 0 else 0
            ),
            "average_processing_time": (
                self.total_processing_time / self.successful_count
                if self.successful_count > 0
                else 0
            ),
            "average_confidence": self.average_confidence,
        }


_metrics = ProcessingMetrics()


def get_processing_metrics() -> Dict[str, Any]:
    """Get current processing metrics."""
    return _metrics.get_summary()
