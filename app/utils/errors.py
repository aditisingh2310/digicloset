"""
Standardized error response utilities.

Provides consistent JSON error schema across the application:
  {
    "error": "Human-readable error message",
    "code": "ERROR_CODE_CONSTANT",
    "request_id": "unique-request-id",
    "detail": "Optional additional context",
    "status": 400
  }

Never exposes internal stack traces in production.
"""
import uuid
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """Standard error codes for the application."""
    
    # Authentication & Authorization (4xx)
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    EXPIRED_TOKEN = "EXPIRED_TOKEN"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    TENANT_REQUIRED = "TENANT_REQUIRED"
    
    # Validation (422)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_INPUT = "INVALID_INPUT"
    
    # Rate Limiting (429)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    
    # Abuse Protection (400/429)
    PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
    INPUT_SIZE_EXCEEDED = "INPUT_SIZE_EXCEEDED"
    SKU_LIST_TOO_LONG = "SKU_LIST_TOO_LONG"
    TIMEOUT_EXCEEDED = "TIMEOUT_EXCEEDED"
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"
    
    # Business Logic (400)
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
    
    # Server Errors (5xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    DEPENDENCY_FAILED = "DEPENDENCY_FAILED"


class APIError(HTTPException):
    """Production-grade API error with request_id tracking."""
    
    def __init__(
        self,
        status_code: int = 500,
        error: str = "Internal Server Error",
        code: str = ErrorCode.INTERNAL_ERROR,
        detail: str = "",
        request_id: str = None,
        headers: Dict[str, str] = None,
    ):
        self.status_code = status_code
        self.error = error
        self.code = code
        self.detail = detail
        self.request_id = request_id or str(uuid.uuid4())
        self.headers = headers or {}
        
        # Build response
        response_body = {
            "error": error,
            "code": code,
            "request_id": self.request_id,
            "status": status_code,
        }
        
        if detail:
            response_body["detail"] = detail
        
        super().__init__(
            status_code=status_code,
            detail=response_body,
            headers=self.headers,
        )


class ErrorResponse:
    """Builder for standardized error responses."""
    
    def __init__(self, request_id: str = None):
        self.request_id = request_id or str(uuid.uuid4())
    
    @staticmethod
    def build(
        status_code: int,
        error: str,
        code: ErrorCode,
        detail: str = "",
        request_id: str = None,
    ) -> Dict[str, Any]:
        """Build error response dict."""
        request_id = request_id or str(uuid.uuid4())
        
        response = {
            "error": error,
            "code": code,
            "request_id": request_id,
            "status": status_code,
        }
        
        if detail:
            response["detail"] = detail
        
        return response
    
    @staticmethod
    def bad_request(
        detail: str = "Invalid request",
        code: ErrorCode = ErrorCode.INVALID_INPUT,
        request_id: str = None,
    ) -> Dict[str, Any]:
        """400 Bad Request."""
        return ErrorResponse.build(
            status_code=400,
            error="Bad Request",
            code=code,
            detail=detail,
            request_id=request_id,
        )
    
    @staticmethod
    def unauthorized(
        detail: str = "Authentication required",
        code: ErrorCode = ErrorCode.INVALID_CREDENTIALS,
        request_id: str = None,
    ) -> Dict[str, Any]:
        """401 Unauthorized."""
        return ErrorResponse.build(
            status_code=401,
            error="Unauthorized",
            code=code,
            detail=detail,
            request_id=request_id,
        )
    
    @staticmethod
    def forbidden(
        detail: str = "Insufficient permissions",
        code: ErrorCode = ErrorCode.INSUFFICIENT_PERMISSIONS,
        request_id: str = None,
    ) -> Dict[str, Any]:
        """403 Forbidden."""
        return ErrorResponse.build(
            status_code=403,
            error="Forbidden",
            code=code,
            detail=detail,
            request_id=request_id,
        )
    
    @staticmethod
    def not_found(
        resource_type: str = "Resource",
        request_id: str = None,
    ) -> Dict[str, Any]:
        """404 Not Found."""
        return ErrorResponse.build(
            status_code=404,
            error=f"{resource_type} not found",
            code=ErrorCode.RESOURCE_NOT_FOUND,
            detail=f"The requested {resource_type} does not exist",
            request_id=request_id,
        )
    
    @staticmethod
    def conflict(
        resource_type: str = "Resource",
        request_id: str = None,
    ) -> Dict[str, Any]:
        """409 Conflict."""
        return ErrorResponse.build(
            status_code=409,
            error=f"{resource_type} already exists",
            code=ErrorCode.RESOURCE_ALREADY_EXISTS,
            detail=f"A {resource_type} with this identity already exists",
            request_id=request_id,
        )
    
    @staticmethod
    def validation_error(
        detail: str = "Request validation failed",
        request_id: str = None,
    ) -> Dict[str, Any]:
        """422 Unprocessable Entity."""
        return ErrorResponse.build(
            status_code=422,
            error="Validation Error",
            code=ErrorCode.VALIDATION_ERROR,
            detail=detail,
            request_id=request_id,
        )
    
    @staticmethod
    def rate_limit(
        detail: str = "Too many requests",
        retry_after: int = 60,
        request_id: str = None,
    ) -> tuple[Dict[str, Any], Dict[str, str]]:
        """429 Too Many Requests with Retry-After header."""
        response = ErrorResponse.build(
            status_code=429,
            error="Too Many Requests",
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            detail=detail,
            request_id=request_id,
        )
        response["retry_after_seconds"] = retry_after
        
        headers = {
            "Retry-After": str(retry_after),
            "X-Request-ID": request_id or str(uuid.uuid4()),
        }
        
        return response, headers
    
    @staticmethod
    def payload_too_large(
        max_size_mb: float = None,
        request_id: str = None,
    ) -> Dict[str, Any]:
        """413 Payload Too Large."""
        detail = "Request payload too large"
        if max_size_mb:
            detail += f" (max: {max_size_mb}MB)"
        
        return ErrorResponse.build(
            status_code=413,
            error="Payload Too Large",
            code=ErrorCode.PAYLOAD_TOO_LARGE,
            detail=detail,
            request_id=request_id,
        )
    
    @staticmethod
    def internal_error(
        request_id: str = None,
        show_detail: bool = False,
        detail: str = None,
    ) -> Dict[str, Any]:
        """500 Internal Server Error (never exposes stack trace in production)."""
        response_detail = (
            detail if detail and show_detail
            else "An internal server error occurred. Please contact support."
        )
        
        return ErrorResponse.build(
            status_code=500,
            error="Internal Server Error",
            code=ErrorCode.INTERNAL_ERROR,
            detail=response_detail,
            request_id=request_id,
        )


class RequestIDMiddleware:
    """Middleware to add request_id to all responses."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, request: Request, call_next):
        # Generate or extract request_id
        request_id = request.headers.get(
            "X-Request-ID",
            str(uuid.uuid4())
        )
        
        # Store in request state
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add request_id to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response


async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected exceptions without exposing stack traces.
    
    Usage:
        from fastapi import FastAPI
        from fastapi.exceptions import HTTPException
        
        app = FastAPI()
        app.add_exception_handler(Exception, general_exception_handler)
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    logger.error(
        f"Unhandled exception: {type(exc).__name__}",
        exc_info=True,
        extra={"request_id": request_id}
    )
    
    # Never expose stack trace in production
    response = ErrorResponse.internal_error(request_id=request_id, show_detail=False)
    
    return JSONResponse(
        status_code=500,
        content=response,
        headers={"X-Request-ID": request_id},
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTPException with request_id."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    # If already structured, pass through
    if isinstance(exc.detail, dict) and "request_id" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
            headers={**exc.headers, "X-Request-ID": request_id},
        )
    
    # Build standardized response
    response = ErrorResponse.build(
        status_code=exc.status_code,
        error=exc.detail or "Request Error",
        code=ErrorCode.INVALID_INPUT,
        request_id=request_id,
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response,
        headers={**exc.headers, "X-Request-ID": request_id},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with request_id."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    # Extract field-level errors
    errors = []
    for error in exc.errors():
        field = ".".join(str(x) for x in error.get("loc", []))
        msg = error.get("msg", "Validation error")
        errors.append(f"{field}: {msg}")
    
    response = ErrorResponse.build(
        status_code=422,
        error="Validation Error",
        code=ErrorCode.VALIDATION_ERROR,
        detail="; ".join(errors) if errors else "Request validation failed",
        request_id=request_id,
    )
    
    return JSONResponse(
        status_code=422,
        content=response,
        headers={"X-Request-ID": request_id},
    )


# Helper for use in endpoints
def get_request_id(request: Request) -> str:
    """Get request_id from request state."""
    return getattr(request.state, "request_id", str(uuid.uuid4()))
