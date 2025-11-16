"""
Custom exception handlers for enhanced API error responses.

Provides user-friendly error messages with proper error codes
for better frontend integration and debugging.
"""

import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import (
    PermissionDenied,
    ValidationError as DjangoValidationError,
)
from django.http import Http404

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides enhanced error responses.

    Returns structured error responses with:
    - error_code: Machine-readable error code
    - message: Technical error message
    - user_message: User-friendly error message
    - dev_details: Additional details for debugging (DEBUG mode only)
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    # Get request for logging
    request = context.get("view").request if context.get("view") else None

    if response is not None:
        # Enhance the response with additional context
        custom_response_data = {
            "error_code": get_error_code(exc),
            "message": get_error_message(exc),
            "user_message": get_user_friendly_message(exc),
        }

        # Add original errors if they exist
        if isinstance(response.data, dict):
            if "detail" in response.data:
                custom_response_data["detail"] = response.data["detail"]
            else:
                custom_response_data["errors"] = response.data

        # Log the error
        if response.status_code >= 500:
            logger.error(
                f"Server error: {exc.__class__.__name__}: {str(exc)}, "
                f"path={request.path if request else 'unknown'}, "
                f"user={request.user if request and request.user.is_authenticated else 'anonymous'}"
            )
        elif response.status_code >= 400:
            logger.warning(
                f"Client error: {exc.__class__.__name__}: {str(exc)}, "
                f"path={request.path if request else 'unknown'}"
            )

        response.data = custom_response_data

    else:
        # Handle Django's built-in exceptions
        if isinstance(exc, Http404):
            logger.info(f"404 Not Found: {str(exc)}")
            response = Response(
                {
                    "error_code": "NOT_FOUND",
                    "message": "The requested resource was not found.",
                    "user_message": "We couldn't find what you're looking for.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        elif isinstance(exc, PermissionDenied):
            logger.warning(f"Permission denied: {str(exc)}")
            response = Response(
                {
                    "error_code": "PERMISSION_DENIED",
                    "message": "You do not have permission to perform this action.",
                    "user_message": "Sorry, you don't have access to this resource.",
                    "hint": "Contact your household admin if you believe this is an error.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        elif isinstance(exc, DjangoValidationError):
            logger.warning(f"Validation error: {str(exc)}")
            response = Response(
                {
                    "error_code": "VALIDATION_ERROR",
                    "message": "The data provided is invalid.",
                    "user_message": "Please check your input and try again.",
                    "errors": (
                        exc.message_dict if hasattr(exc, "message_dict") else str(exc)
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            # Unhandled exception
            logger.error(
                f"Unhandled exception: {exc.__class__.__name__}: {str(exc)}",
                exc_info=True,
            )
            response = Response(
                {
                    "error_code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred.",
                    "user_message": "Something went wrong. Our team has been notified.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    return response


def get_error_code(exc):
    """Get a machine-readable error code from the exception."""
    if hasattr(exc, "default_code"):
        return exc.default_code.upper()
    return exc.__class__.__name__.upper()


def get_error_message(exc):
    """Get the technical error message."""
    if hasattr(exc, "detail"):
        if isinstance(exc.detail, dict):
            return str(exc.detail)
        return str(exc.detail)
    return str(exc)


def get_user_friendly_message(exc):
    """Get a user-friendly error message."""
    error_messages = {
        "NotAuthenticated": "Please log in to access this resource.",
        "AuthenticationFailed": "Your session has expired. Please log in again.",
        "PermissionDenied": "You don't have permission to perform this action.",
        "NotFound": "The item you're looking for doesn't exist.",
        "ValidationError": "Please check your input and try again.",
        "Throttled": "You're making too many requests. Please slow down.",
        "MethodNotAllowed": "This action is not supported.",
        "ParseError": "We couldn't understand your request. Please check the format.",
        "UnsupportedMediaType": "The file type you uploaded is not supported.",
    }

    exc_class = exc.__class__.__name__
    return error_messages.get(exc_class, "An error occurred. Please try again.")
