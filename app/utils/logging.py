"""
PII-safe logging utilities for production environments.

Features:
- Mask access tokens and API keys
- Partially mask shop domains
- Never log raw headers
- Safe logging wrapper with automatic redaction
- Request/response logging without sensitive data
"""
import logging
import re
import json
from typing import Any, Dict, Optional
from datetime import datetime
import hashlib


class PIISafeFormatter(logging.Formatter):
    """Logging formatter that redacts PII from log records."""
    
    # Token patterns
    TOKEN_PATTERNS = [
        (r'bearer\s+(\S+)', 'Bearer ***REDACTED***'),
        (r'authorization:\s*(\S+)', 'Authorization: ***REDACTED***'),
        (r'x-api-key:\s*(\S+)', 'X-API-Key: ***REDACTED***'),
        (r'api[_-]?key["\']?\s*[:=]\s*["\']?(\S+?)["\']?(?:\s|,|$)', 'api_key: ***REDACTED***'),
        (r'password["\']?\s*[:=]\s*["\']?(\S+?)["\']?(?:\s|,|$)', 'password: ***REDACTED***'),
        (r'secret["\']?\s*[:=]\s*["\']?(\S+?)["\']?(?:\s|,|$)', 'secret: ***REDACTED***'),
        (r'token["\']?\s*[:=]\s*["\']?(\S+?)["\']?(?:\s|,|$)', 'token: ***REDACTED***'),
        (r'access[_-]?token["\']?\s*[:=]\s*["\']?(\S+?)["\']?(?:\s|,|$)', 'access_token: ***REDACTED***'),
    ]
    
    # Shop domain masking
    SHOP_DOMAIN_PATTERN = r'([a-z0-9]+)\.myshopify\.com'
    
    # Email masking
    EMAIL_PATTERN = r'(\w)[a-z0-9._%+-]*@[a-z0-9.-]+\.\w+'
    
    @staticmethod
    def _mask_token(msg: str) -> str:
        """Remove bearer tokens and API keys from message."""
        for pattern, replacement in PIISafeFormatter.TOKEN_PATTERNS:
            msg = re.sub(pattern, replacement, msg, flags=re.IGNORECASE)
        return msg
    
    @staticmethod
    def _mask_shop_domain(msg: str) -> str:
        """Partially mask shop domain (show first 3 chars only)."""
        def replace_domain(match):
            shop_name = match.group(1)
            if len(shop_name) <= 3:
                masked = shop_name[0] + '*' * (len(shop_name) - 1)
            else:
                masked = shop_name[:3] + '*' * (len(shop_name) - 3)
            return f"{masked}.myshopify.com"
        
        return re.sub(
            PIISafeFormatter.SHOP_DOMAIN_PATTERN,
            replace_domain,
            msg,
            flags=re.IGNORECASE
        )
    
    @staticmethod
    def _mask_email(msg: str) -> str:
        """Mask email addresses (show only first char and domain)."""
        def replace_email(match):
            first_char = match.group(1)
            # Extract domain from full match
            email_match = re.search(r'@([a-z0-9.-]+\.\w+)', match.group(0))
            if email_match:
                domain = email_match.group(1)
                return f"{first_char}***@{domain}"
            return "***@***"
        
        return re.sub(
            PIISafeFormatter.EMAIL_PATTERN,
            replace_email,
            msg,
            flags=re.IGNORECASE
        )
    
    @staticmethod
    def _mask_credit_card(msg: str) -> str:
        """Mask credit card numbers (show only last 4 digits)."""
        # Visa, Mastercard, Amex patterns
        pattern = r'\b(?:\d{4}[\s-]?){3}\d{4}\b'
        return re.sub(pattern, '****-****-****-****', msg)
    
    @staticmethod
    def _mask_ssn(msg: str) -> str:
        """Mask social security numbers."""
        pattern = r'\b\d{3}-\d{2}-(\d{4})\b'
        return re.sub(pattern, r'***-**-\1', msg)
    
    @staticmethod
    def sanitize(msg: Any) -> str:
        """Apply all sanitization rules."""
        if not isinstance(msg, str):
            msg = str(msg)
        
        msg = PIISafeFormatter._mask_token(msg)
        msg = PIISafeFormatter._mask_shop_domain(msg)
        msg = PIISafeFormatter._mask_email(msg)
        msg = PIISafeFormatter._mask_credit_card(msg)
        msg = PIISafeFormatter._mask_ssn(msg)
        
        return msg
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with PII redaction."""
        # Sanitize message
        record.msg = self.sanitize(str(record.msg))
        
        # Sanitize args if present
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self.sanitize(v) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self.sanitize(arg) for arg in record.args)
        
        # Sanitize exception info if present
        if record.exc_text:
            record.exc_text = self.sanitize(record.exc_text)
        
        return super().format(record)


def setup_pii_safe_logging(
    logger_name: str = None,
    level: int = logging.INFO,
    format_string: str = None,
) -> logging.Logger:
    """
    Configure PII-safe logging for a logger.
    
    Usage:
        logger = setup_pii_safe_logging(__name__)
        logger.info(f"User: {user}, Token: {token}")
        # Output: User: ..., Token: ***REDACTED***
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create handler with safe formatter
    handler = logging.StreamHandler()
    handler.setLevel(level)
    
    fmt = format_string or (
        "[%(asctime)s] %(name)s - %(levelname)s - %(message)s"
    )
    formatter = PIISafeFormatter(fmt)
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    return logger


def safe_log(
    message: str,
    logger: logging.Logger = None,
    level: str = "info",
    **kwargs
) -> None:
    """
    Safely log a message with automatic PII redaction.
    
    Args:
        message: Log message (may contain PII)
        logger: Logger instance (uses root logger if None)
        level: Log level ("debug", "info", "warning", "error")
        **kwargs: Additional context to log (will be redacted)
    
    Usage:
        safe_log("User login", shop_id=shop_id, token=token)
    """
    if logger is None:
        logger = logging.getLogger()
    
    # Sanitize message and kwargs
    message = PIISafeFormatter.sanitize(message)
    
    context = {}
    for key, value in kwargs.items():
        context[key] = PIISafeFormatter.sanitize(value)
    
    # Add context to message if present
    if context:
        try:
            context_str = json.dumps(context, default=str)
            context_str = PIISafeFormatter.sanitize(context_str)
            message = f"{message} | {context_str}"
        except Exception:
            pass
    
    # Log at appropriate level
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(message)


class RequestLogger:
    """Safely log HTTP requests without exposing sensitive data."""
    
    SENSITIVE_HEADERS = {
        "authorization",
        "x-api-key",
        "x-auth-token",
        "cookie",
        "x-csrf-token",
    }
    
    @staticmethod
    def _safe_headers(headers: Dict[str, str]) -> Dict[str, str]:
        """Return headers with sensitive values redacted."""
        safe = {}
        for key, value in headers.items():
            if key.lower() in RequestLogger.SENSITIVE_HEADERS:
                safe[key] = "***REDACTED***"
            else:
                safe[key] = PIISafeFormatter.sanitize(value)
        return safe
    
    @staticmethod
    def log_request(
        logger: logging.Logger,
        method: str,
        path: str,
        headers: Dict[str, str] = None,
        query_params: Dict[str, str] = None,
    ) -> None:
        """Log HTTP request safely."""
        safe_headers = RequestLogger._safe_headers(headers or {})
        safe_params = {
            k: PIISafeFormatter.sanitize(v)
            for k, v in (query_params or {}).items()
        }
        
        logger.info(
            f"HTTP {method} {path}",
            extra={
                "headers": safe_headers,
                "query_params": safe_params,
            }
        )
    
    @staticmethod
    def log_response(
        logger: logging.Logger,
        status_code: int,
        response_time_ms: float,
        response_size_bytes: int = None,
    ) -> None:
        """Log HTTP response safely."""
        msg = f"HTTP Response: {status_code} ({response_time_ms:.1f}ms"
        if response_size_bytes:
            msg += f", {response_size_bytes} bytes"
        msg += ")"
        logger.info(msg)
    
    @staticmethod
    def log_error(
        logger: logging.Logger,
        error: Exception,
        context: Dict[str, Any] = None,
    ) -> None:
        """Log errors with context, redacting sensitive data."""
        safe_context = {}
        for key, value in (context or {}).items():
            safe_context[key] = PIISafeFormatter.sanitize(value)
        
        logger.error(
            f"Error: {type(error).__name__}",
            exc_info=True,
            extra={"context": safe_context}
        )


class AuditLogger:
    """Audit logging for security events (redacted)."""
    
    def __init__(self, logger_name: str = "audit"):
        self.logger = setup_pii_safe_logging(logger_name)
    
    def log_authentication(self, shop_id: str, method: str, success: bool) -> None:
        """Log authentication attempt."""
        self.logger.info(
            f"Authentication attempt",
            extra={
                "shop_id": shop_id,
                "method": method,
                "success": success,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    
    def log_authorization_failure(
        self,
        shop_id: str,
        action: str,
        resource_id: str,
        reason: str,
    ) -> None:
        """Log authorization denial."""
        self.logger.warning(
            f"Authorization denied",
            extra={
                "shop_id": shop_id,
                "action": action,
                "resource_id": resource_id,
                "reason": reason,
            }
        )
    
    def log_data_access(
        self,
        shop_id: str,
        entity_type: str,
        entity_id: str,
        operation: str,
    ) -> None:
        """Log data access for compliance."""
        self.logger.info(
            f"Data access",
            extra={
                "shop_id": shop_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "operation": operation,
            }
        )
    
    def log_rate_limit_exceeded(
        self,
        shop_id: str,
        ip_address: str,
        endpoint: str,
        limit_category: str,
    ) -> None:
        """Log rate limit violations."""
        self.logger.warning(
            f"Rate limit exceeded",
            extra={
                "shop_id": shop_id,
                "ip_address": ip_address,
                "endpoint": endpoint,
                "limit_category": limit_category,
            }
        )
