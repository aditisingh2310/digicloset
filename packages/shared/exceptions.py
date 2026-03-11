"""
Shared error handling and exceptions.
"""

from typing import Optional, Any, Dict
import logging

logger = logging.getLogger(__name__)


class DigiClosetException(Exception):
    """Base exception for DigiCloset application."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code or "INTERNAL_ERROR"
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
            "status_code": self.status_code,
        }


class ValidationError(DigiClosetException):
    """Validation error."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "VALIDATION_ERROR", 400, details)


class AuthenticationError(DigiClosetException):
    """Authentication error."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTHENTICATION_ERROR", 401)


class AuthorizationError(DigiClosetException):
    """Authorization error."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, "AUTHORIZATION_ERROR", 403)


class NotFoundError(DigiClosetException):
    """Resource not found error."""

    def __init__(self, resource: str, resource_id: Optional[str] = None):
        message = f"{resource} not found"
        if resource_id:
            message += f": {resource_id}"
        super().__init__(message, "NOT_FOUND", 404)


class ConflictError(DigiClosetException):
    """Resource conflict error."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONFLICT", 409, details)


class RateLimitError(DigiClosetException):
    """Rate limit exceeded error."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60):
        super().__init__(message, "RATE_LIMIT_EXCEEDED", 429, {"retry_after": retry_after})


class ExternalServiceError(DigiClosetException):
    """External service error (Shopify, Replicate, etc.)."""

    def __init__(self, service: str, message: str, details: Optional[Dict[str, Any]] = None):
        full_message = f"{service} service error: {message}"
        super().__init__(full_message, "EXTERNAL_SERVICE_ERROR", 502, details)


def handle_exception(exc: Exception) -> Dict[str, Any]:
    """
    Convert exception to standard response format.

    Args:
        exc: The exception to handle

    Returns:
        Dictionary with error response
    """
    if isinstance(exc, DigiClosetException):
        return exc.to_dict()

    # Log unexpected exceptions
    logger.exception("Unexpected exception", exc_info=exc)

    return {
        "error": "INTERNAL_SERVER_ERROR",
        "message": "An unexpected error occurred",
        "status_code": 500,
    }
