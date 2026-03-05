"""Production-grade utility modules for FastAPI applications."""

from .logging import (
    PIISafeFormatter,
    setup_pii_safe_logging,
    safe_log,
    RequestLogger,
    AuditLogger,
)
from .errors import (
    ErrorCode,
    APIError,
    ErrorResponse,
    RequestIDMiddleware,
    get_request_id,
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from .abuse_protection import (
    AbuseProtectionConfig,
    AbuseProtectionError,
    PayloadValidator,
    TimeoutGuard,
    InputSanitizer,
    SKUListInput,
    AIAnalysisInput,
    BatchProcessingInput,
    check_abuse_limits,
)

__all__ = [
    # Logging
    "PIISafeFormatter",
    "setup_pii_safe_logging",
    "safe_log",
    "RequestLogger",
    "AuditLogger",
    # Errors
    "ErrorCode",
    "APIError",
    "ErrorResponse",
    "RequestIDMiddleware",
    "get_request_id",
    "general_exception_handler",
    "http_exception_handler",
    "validation_exception_handler",
    # Abuse Protection
    "AbuseProtectionConfig",
    "AbuseProtectionError",
    "PayloadValidator",
    "TimeoutGuard",
    "InputSanitizer",
    "SKUListInput",
    "AIAnalysisInput",
    "BatchProcessingInput",
    "check_abuse_limits",
]
