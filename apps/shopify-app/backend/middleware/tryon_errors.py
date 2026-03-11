"""
Error Handling Middleware for Try-On Service

Comprehensive error handling, validation, and logging middleware
for virtual try-on operations.
"""

import logging
import json
from datetime import datetime
from typing import Callable, Any
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


# ============ Error Classes ============


class TryOnError(Exception):
    """Base exception for try-on operations."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: dict = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(TryOnError):
    """Validation error during try-on request."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class InvalidImageError(TryOnError):
    """Image validation error."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="INVALID_IMAGE",
            details=details,
        )


class InsufficientCreditsError(TryOnError):
    """Shop has no credits available."""

    def __init__(self, remaining: int = 0):
        super().__init__(
            message="Insufficient credits for try-on generation",
            status_code=402,  # Payment Required
            error_code="INSUFFICIENT_CREDITS",
            details={"credits_remaining": remaining},
        )


class RateLimitError(TryOnError):
    """Rate limit exceeded."""

    def __init__(self, retry_after: int = 60):
        super().__init__(
            message="Too many try-on requests. Please try again later.",
            status_code=429,  # Too Many Requests
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after},
        )


class ImageProcessingError(TryOnError):
    """Error during image processing."""

    def __init__(self, message: str = "Failed to process image"):
        super().__init__(
            message=message,
            status_code=400,
            error_code="IMAGE_PROCESSING_ERROR",
        )


class InferenceServiceError(TryOnError):
    """Error from inference service."""

    def __init__(self, message: str = "Inference service error"):
        super().__init__(
            message=message,
            status_code=502,  # Bad Gateway
            error_code="INFERENCE_SERVICE_ERROR",
        )


class DatabaseError(TryOnError):
    """Database operation error."""

    def __init__(self, message: str = "Database error"):
        super().__init__(
            message=message,
            status_code=500,
            error_code="DATABASE_ERROR",
        )


class StorageError(TryOnError):
    """Storage operation error."""

    def __init__(self, message: str = "Storage error"):
        super().__init__(
            message=message,
            status_code=500,
            error_code="STORAGE_ERROR",
        )


class AuthenticationError(TryOnError):
    """Authentication failed."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR",
        )


# ============ Error Response ============


class ErrorResponse:
    """Standardized error response format."""

    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = 500,
        details: dict = None,
        request_id: str = None,
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.request_id = request_id
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON response."""
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "timestamp": self.timestamp,
                "request_id": self.request_id,
            },
            "details": self.details,
        }


# ============ Error Handling Middleware ============


class TryOnErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware for handling try-on specific errors."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and handle errors."""
        # Generate request ID for tracing
        request_id = request.headers.get("x-request-id") or _generate_request_id()
        request.state.request_id = request_id

        try:
            # Check rate limiting before processing
            if request.url.path.startswith("/api/v1/try-on"):
                await self._check_rate_limit(request)

            # Process request
            response = await call_next(request)

            # Log successful response
            self._log_request(request, response, request_id)

            return response

        except TryOnError as e:
            logger.error(
                f"Try-on error: {e.error_code}",
                extra={
                    "error_code": e.error_code,
                    "message": e.message,
                    "request_id": request_id,
                    "details": e.details,
                },
            )
            return self._error_response(e, request_id)

        except Exception as e:
            logger.exception(
                f"Unexpected error: {str(e)}",
                extra={"request_id": request_id},
            )
            error = TryOnError(
                message="Internal server error",
                status_code=500,
                error_code="INTERNAL_ERROR",
            )
            return self._error_response(error, request_id)

    async def _check_rate_limit(self, request: Request) -> None:
        """Check if request exceeds rate limit."""
        shop_id = getattr(request.state, "shop_id", None)
        if not shop_id:
            return

        # This is pseudo-code - implement with Redis or similar
        # redis_key = f"tryon_limit:{shop_id}"
        # current = redis.incr(redis_key)
        # redis.expire(redis_key, 60)  # 1 minute window
        #
        # max_per_minute = os.getenv("RATE_LIMIT_TRYONS_PER_MINUTE", 10)
        # if current > int(max_per_minute):
        #     raise RateLimitError(retry_after=60)

        pass

    def _error_response(self, error: TryOnError, request_id: str) -> JSONResponse:
        """Create JSON error response."""
        error_response = ErrorResponse(
            error_code=error.error_code,
            message=error.message,
            status_code=error.status_code,
            details=error.details,
            request_id=request_id,
        )

        return JSONResponse(
            status_code=error.status_code,
            content=error_response.to_dict(),
        )

    def _log_request(self, request: Request, response: Response, request_id: str) -> None:
        """Log successful request."""
        logger.info(
            f"{request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "request_id": request_id,
            },
        )


# ============ Structured Logging ============


class TryOnLogger:
    """Structured logging for try-on operations."""

    @staticmethod
    def log_generation_started(
        tryon_id: str,
        shop_id: str,
        category: str,
        request_id: str = None,
    ) -> None:
        """Log try-on generation start."""
        logger.info(
            "Try-on generation started",
            extra={
                "event": "generation_start",
                "tryon_id": tryon_id,
                "shop_id": shop_id,
                "category": category,
                "request_id": request_id,
            },
        )

    @staticmethod
    def log_generation_completed(
        tryon_id: str,
        shop_id: str,
        processing_time: float,
        image_url: str,
        request_id: str = None,
    ) -> None:
        """Log try-on generation completion."""
        logger.info(
            "Try-on generation completed",
            extra={
                "event": "generation_complete",
                "tryon_id": tryon_id,
                "shop_id": shop_id,
                "processing_time": processing_time,
                "image_url": image_url,
                "request_id": request_id,
            },
        )

    @staticmethod
    def log_generation_failed(
        tryon_id: str,
        shop_id: str,
        error: str,
        error_code: str = None,
        request_id: str = None,
    ) -> None:
        """Log try-on generation failure."""
        logger.error(
            "Try-on generation failed",
            extra={
                "event": "generation_failed",
                "tryon_id": tryon_id,
                "shop_id": shop_id,
                "error": error,
                "error_code": error_code,
                "request_id": request_id,
            },
        )

    @staticmethod
    def log_credit_check(
        shop_id: str,
        credits_remaining: int,
        request_id: str = None,
    ) -> None:
        """Log credit check."""
        logger.info(
            "Credit check",
            extra={
                "event": "credit_check",
                "shop_id": shop_id,
                "credits_remaining": credits_remaining,
                "request_id": request_id,
            },
        )

    @staticmethod
    def log_image_validation(
        tryon_id: str,
        image_size_mb: float,
        image_url: str,
        valid: bool = True,
        error: str = None,
        request_id: str = None,
    ) -> None:
        """Log image validation."""
        event = "image_validation_pass" if valid else "image_validation_fail"
        logger.info(
            event,
            extra={
                "event": event,
                "tryon_id": tryon_id,
                "image_size_mb": image_size_mb,
                "image_url": image_url,
                "error": error,
                "request_id": request_id,
            },
        )

    @staticmethod
    def log_api_call(
        service: str,
        endpoint: str,
        method: str = "POST",
        duration_ms: float = None,
        status_code: int = None,
        error: str = None,
        request_id: str = None,
    ) -> None:
        """Log API call."""
        logger.info(
            f"{service} API call",
            extra={
                "event": "api_call",
                "service": service,
                "endpoint": endpoint,
                "method": method,
                "duration_ms": duration_ms,
                "status_code": status_code,
                "error": error,
                "request_id": request_id,
            },
        )


# ============ Validation Utilities ============


class TryOnValidator:
    """Validation utilities for try-on requests."""

    @staticmethod
    def validate_image_url(url: str) -> None:
        """Validate image URL format and accessibility."""
        if not url:
            raise ValidationError("Image URL is required")

        if not url.startswith(("http://", "https://", "s3://")):
            raise ValidationError("Invalid image URL format")

        # Add additional validation as needed
        # - Check URL accessibility
        # - Verify file size
        # - Check image format

    @staticmethod
    def validate_category(category: str) -> None:
        """Validate clothing category."""
        valid_categories = [
            "upper_body",
            "lower_body",
            "full_body",
            "dress",
            "accessories",
        ]

        if category not in valid_categories:
            raise ValidationError(
                f"Invalid category: {category}",
                details={"valid_categories": valid_categories},
            )

    @staticmethod
    def validate_product_id(product_id: str) -> None:
        """Validate product ID format."""
        if not product_id:
            raise ValidationError("Product ID is required")

        # Validate Shopify product ID format
        if not product_id.isdigit() and not product_id.startswith("gid://"):
            raise ValidationError("Invalid product ID format")


# ============ Utility Functions ============


def _generate_request_id() -> str:
    """Generate unique request ID."""
    import uuid
    return str(uuid.uuid4())[:8]


def setup_error_handlers(app) -> None:
    """Setup error handling for FastAPI app."""
    # Add middleware
    app.add_middleware(TryOnErrorHandlerMiddleware)

    # Add exception handlers
    @app.exception_handler(TryOnError)
    async def tryon_error_handler(request: Request, exc: TryOnError):
        request_id = getattr(request.state, "request_id", None)
        error_response = ErrorResponse(
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details,
            request_id=request_id,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.to_dict(),
        )

    @app.exception_handler(Exception)
    async def general_error_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", None)
        logger.exception(
            f"Unhandled exception: {str(exc)}",
            extra={"request_id": request_id},
        )
        error_response = ErrorResponse(
            error_code="INTERNAL_ERROR",
            message="Internal server error",
            status_code=500,
            request_id=request_id,
        )
        return JSONResponse(
            status_code=500,
            content=error_response.to_dict(),
        )
