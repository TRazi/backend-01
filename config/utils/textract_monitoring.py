"""
Monitoring and Observability for AWS Textract Integration

Provides Sentry integration, metrics collection, and alerting for OCR operations.
Complies with Privacy Act 2020 by masking sensitive data in logs.
"""

import logging
import time
import functools
from typing import Optional, Callable, Any
from datetime import datetime, timedelta
from enum import Enum

from django.utils import timezone
from django.conf import settings

try:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

logger = logging.getLogger(__name__)


# ============================================================================
# Severity Levels
# ============================================================================


class AlertSeverity(Enum):
    """Alert severity levels for monitoring."""
    
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics to track."""
    
    COUNTER = "counter"
    TIMER = "timer"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


# ============================================================================
# Metrics Collection
# ============================================================================


class ProcessingMetrics:
    """Collect and aggregate OCR processing metrics."""
    
    def __init__(self):
        """Initialize metrics collection."""
        self._data = {
            'uploads_total': 0,
            'uploads_successful': 0,
            'uploads_failed': 0,
            'uploads_duplicate': 0,
            'uploads_invalid': 0,
            'processing_times': [],
            'confidence_scores': [],
            'error_codes': {},
            'last_reset': timezone.now(),
        }
    
    def record_upload(self, file_size: int, is_duplicate: bool = False):
        """Record file upload event."""
        self._data['uploads_total'] += 1
        if is_duplicate:
            self._data['uploads_duplicate'] += 1
    
    def record_processing_start(self, attachment_id: str):
        """Record processing start time."""
        return timezone.now()
    
    def record_processing_success(
        self,
        attachment_id: str,
        processing_time: float,
        confidence_scores: dict
    ):
        """Record successful processing."""
        self._data['uploads_successful'] += 1
        self._data['processing_times'].append(processing_time)
        if confidence_scores:
            avg_confidence = sum(confidence_scores.values()) / len(confidence_scores)
            self._data['confidence_scores'].append(avg_confidence)
    
    def record_processing_failure(
        self,
        attachment_id: str,
        error_code: str,
        is_validation_error: bool = False
    ):
        """Record failed processing."""
        self._data['uploads_failed'] += 1
        if is_validation_error:
            self._data['uploads_invalid'] += 1
        
        # Track error codes
        if error_code not in self._data['error_codes']:
            self._data['error_codes'][error_code] = 0
        self._data['error_codes'][error_code] += 1
    
    def get_metrics_summary(self) -> dict:
        """Get current metrics summary."""
        total = self._data['uploads_total']
        successful = self._data['uploads_successful']
        failed = self._data['uploads_failed']
        processing_times = self._data['processing_times']
        confidence_scores = self._data['confidence_scores']
        
        return {
            'period': {
                'start': self._data['last_reset'].isoformat(),
                'end': timezone.now().isoformat(),
            },
            'uploads': {
                'total': total,
                'successful': successful,
                'failed': failed,
                'duplicate': self._data['uploads_duplicate'],
                'invalid': self._data['uploads_invalid'],
                'success_rate': (successful / total * 100) if total > 0 else 0,
            },
            'performance': {
                'avg_processing_time_ms': (
                    sum(processing_times) / len(processing_times) * 1000
                    if processing_times else 0
                ),
                'min_processing_time_ms': (
                    min(processing_times) * 1000 if processing_times else 0
                ),
                'max_processing_time_ms': (
                    max(processing_times) * 1000 if processing_times else 0
                ),
                'avg_confidence': (
                    sum(confidence_scores) / len(confidence_scores)
                    if confidence_scores else 0
                ),
            },
            'errors': self._data['error_codes'],
        }
    
    def reset(self):
        """Reset metrics for new period."""
        self._data = {
            'uploads_total': 0,
            'uploads_successful': 0,
            'uploads_failed': 0,
            'uploads_duplicate': 0,
            'uploads_invalid': 0,
            'processing_times': [],
            'confidence_scores': [],
            'error_codes': {},
            'last_reset': timezone.now(),
        }


# Global metrics instance
_metrics = ProcessingMetrics()


# ============================================================================
# Monitoring & Alerting
# ============================================================================


class MonitoringService:
    """Service for monitoring OCR operations and sending alerts."""
    
    @staticmethod
    def initialize_sentry(
        dsn: Optional[str] = None,
        environment: Optional[str] = None,
        traces_sample_rate: float = 0.1
    ):
        """Initialize Sentry error tracking."""
        if not SENTRY_AVAILABLE:
            logger.warning("Sentry SDK not installed. Install via: pip install sentry-sdk")
            return False
        
        dsn = dsn or settings.SENTRY_DSN
        if not dsn:
            logger.info("SENTRY_DSN not configured. Sentry disabled.")
            return False
        
        try:
            sentry_sdk.init(
                dsn=dsn,
                integrations=[
                    DjangoIntegration(),
                    CeleryIntegration(),
                ],
                traces_sample_rate=traces_sample_rate,
                environment=environment or settings.ENVIRONMENT,
                send_default_pii=False,
            )
            logger.info("Sentry initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {e}")
            return False
    
    @staticmethod
    def capture_exception(
        exc: Exception,
        level: AlertSeverity = AlertSeverity.ERROR,
        tags: Optional[dict] = None,
        extra: Optional[dict] = None
    ):
        """Capture exception in Sentry."""
        if not SENTRY_AVAILABLE:
            return
        
        with sentry_sdk.push_scope() as scope:
            if tags:
                for key, value in tags.items():
                    scope.set_tag(key, value)
            
            if extra:
                for key, value in extra.items():
                    scope.set_context(key, value)
            
            scope.set_level(level.value)
            sentry_sdk.capture_exception(exc)
    
    @staticmethod
    def send_alert(
        message: str,
        severity: AlertSeverity,
        tags: Optional[dict] = None,
        extra: Optional[dict] = None
    ):
        """Send alert message to Sentry."""
        if not SENTRY_AVAILABLE:
            logger.log(
                getattr(logging, severity.value.upper(), logging.INFO),
                message
            )
            return
        
        with sentry_sdk.push_scope() as scope:
            if tags:
                for key, value in tags.items():
                    scope.set_tag(key, value)
            
            if extra:
                for key, value in extra.items():
                    scope.set_context(key, value)
            
            scope.set_level(severity.value)
            sentry_sdk.capture_message(message)
    
    @staticmethod
    def check_error_rate(
        window_minutes: int = 5,
        threshold_percent: float = 10.0
    ) -> Optional[dict]:
        """
        Check if error rate exceeds threshold.
        
        Returns alert dict if threshold exceeded, None otherwise.
        """
        metrics = _metrics.get_metrics_summary()
        success_rate = metrics['uploads']['success_rate']
        error_rate = 100 - success_rate
        
        if error_rate > threshold_percent:
            return {
                'alert': True,
                'error_rate': error_rate,
                'threshold': threshold_percent,
                'message': f"Error rate ({error_rate:.1f}%) exceeds threshold ({threshold_percent}%)",
            }
        
        return None
    
    @staticmethod
    def check_processing_time(
        threshold_ms: float = 30000.0,
    ) -> Optional[dict]:
        """
        Check if average processing time exceeds threshold.
        
        Returns alert dict if threshold exceeded, None otherwise.
        """
        metrics = _metrics.get_metrics_summary()
        avg_time = metrics['performance']['avg_processing_time_ms']
        
        if avg_time > threshold_ms:
            return {
                'alert': True,
                'avg_processing_time_ms': avg_time,
                'threshold_ms': threshold_ms,
                'message': f"Avg processing time ({avg_time:.0f}ms) exceeds threshold ({threshold_ms:.0f}ms)",
            }
        
        return None


# ============================================================================
# Decorators for Enhanced Monitoring
# ============================================================================


def monitor_textract_operation(
    operation_name: str,
    capture_args: bool = False,
    alert_on_failure: bool = True
):
    """
    Decorator to monitor Textract operations with timing and error tracking.
    
    Args:
        operation_name: Name of operation for logging
        capture_args: Whether to capture function arguments (be careful with sensitive data)
        alert_on_failure: Send alert to Sentry on failure
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            attachment_id = kwargs.get('attachment_id') or (args[1] if len(args) > 1 else 'unknown')
            
            try:
                result = func(*args, **kwargs)
                
                elapsed_time = time.time() - start_time
                _metrics.record_processing_start(attachment_id)
                
                logger.info(
                    f"{operation_name}_success",
                    extra={
                        "operation": operation_name,
                        "attachment_id": attachment_id,
                        "elapsed_time_ms": int(elapsed_time * 1000),
                        "status": "success",
                    }
                )
                
                return result
            
            except Exception as exc:
                elapsed_time = time.time() - start_time
                error_code = getattr(exc, 'error_code', type(exc).__name__)
                
                # Record metrics
                _metrics.record_processing_failure(attachment_id, str(error_code))
                
                # Log error
                logger.error(
                    f"{operation_name}_failure",
                    extra={
                        "operation": operation_name,
                        "attachment_id": attachment_id,
                        "elapsed_time_ms": int(elapsed_time * 1000),
                        "error_code": str(error_code),
                        "error_message": str(exc)[:100],
                    },
                    exc_info=True
                )
                
                # Send Sentry alert if enabled
                if alert_on_failure:
                    MonitoringService.capture_exception(
                        exc,
                        level=AlertSeverity.ERROR,
                        tags={
                            "operation": operation_name,
                            "attachment_id": attachment_id[:8],
                        },
                        extra={
                            "elapsed_time_ms": int(elapsed_time * 1000),
                        }
                    )
                
                raise
        
        return wrapper
    
    return decorator


def track_performance(func: Callable) -> Callable:
    """Decorator to track function performance and report slow operations."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            
            # Alert if operation takes > 30 seconds
            if elapsed_time > 30:
                logger.warning(
                    f"Slow operation: {func.__name__} took {elapsed_time:.2f}s"
                )
            
            return result
        
        except Exception as exc:
            elapsed_time = time.time() - start_time
            logger.error(
                f"Operation failed: {func.__name__} took {elapsed_time:.2f}s",
                exc_info=True
            )
            raise
    
    return wrapper


def alert_on_threshold(
    metric_type: MetricType,
    threshold: float,
    severity: AlertSeverity = AlertSeverity.WARNING
):
    """
    Decorator to alert when metric exceeds threshold.
    
    Args:
        metric_type: Type of metric (timer, counter, gauge)
        threshold: Threshold value
        severity: Alert severity level
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if metric_type == MetricType.TIMER:
                start_time = time.time()
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                if elapsed > threshold:
                    MonitoringService.send_alert(
                        f"Function {func.__name__} exceeded threshold: {elapsed:.2f}s > {threshold}s",
                        severity=severity,
                        tags={"function": func.__name__, "type": "performance"}
                    )
                
                return result
            
            else:
                # Other metric types
                return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


# ============================================================================
# Health Checks
# ============================================================================


def get_ocr_health_status() -> dict:
    """Get current health status of OCR system."""
    metrics = _metrics.get_metrics_summary()
    error_rate_alert = MonitoringService.check_error_rate()
    processing_time_alert = MonitoringService.check_processing_time()
    
    health_status = 'healthy'
    if error_rate_alert or processing_time_alert:
        health_status = 'degraded'
    
    return {
        'status': health_status,
        'metrics': metrics,
        'alerts': {
            'error_rate': error_rate_alert,
            'processing_time': processing_time_alert,
        },
        'timestamp': timezone.now().isoformat(),
    }


# ============================================================================
# Logging Configuration
# ============================================================================


def configure_textract_logging(
    log_file: str = 'logs/textract.log',
    level: str = 'INFO',
    format_type: str = 'json'
) -> None:
    """
    Configure logging for Textract operations.
    
    Args:
        log_file: Path to log file
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        format_type: Log format (json or verbose)
    """
    import logging.handlers
    import pathlib
    
    # Create log directory if needed
    log_path = pathlib.Path(log_file).parent
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Get Textract logger
    textract_logger = logging.getLogger('config.utils.textract_errors')
    textract_logger.setLevel(getattr(logging, level))
    
    # File handler with rotation
    handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=1024 * 1024 * 10,  # 10MB
        backupCount=5,
    )
    
    # Formatter
    if format_type == 'json':
        try:
            from pythonjsonlogger import jsonlogger
            formatter = jsonlogger.JsonFormatter(
                '%(asctime)s %(name)s %(levelname)s %(message)s'
            )
        except ImportError:
            logger.warning("pythonjsonlogger not installed. Using verbose format.")
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    handler.setFormatter(formatter)
    textract_logger.addHandler(handler)


# ============================================================================
# Exports
# ============================================================================


__all__ = [
    'AlertSeverity',
    'MetricType',
    'ProcessingMetrics',
    'MonitoringService',
    'monitor_textract_operation',
    'track_performance',
    'alert_on_threshold',
    'get_ocr_health_status',
    'configure_textract_logging',
]
