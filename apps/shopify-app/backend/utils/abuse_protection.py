"""
Abuse protection validators for input validation and limits.

Features:
- AI endpoint max input size validation
- SKU list length limits
- Request timeout guards
- Payload size enforcement
- Input sanitization helpers
"""
import asyncio
from typing import List, Optional, Any, Callable, Dict
from functools import wraps
from fastapi import HTTPException, UploadFile
from pydantic import BaseModel, validator, Field
import logging

logger = logging.getLogger(__name__)


class AbuseProtectionConfig:
    """Configuration for abuse protection limits."""
    
    # Payload sizes (bytes)
    MAX_REQUEST_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_IMAGE_SIZE = 25 * 1024 * 1024    # 25MB per image
    MAX_JSON_SIZE = 5 * 1024 * 1024      # 5MB for JSON
    
    # AI endpoints
    MAX_AI_INPUT_LENGTH = 10_000          # characters
    MAX_AI_IMAGE_COUNT = 5                # max images per request
    MAX_AI_BATCH_SIZE = 100               # max items in batch
    
    # Data limits
    MAX_SKU_LIST_LENGTH = 1000             # max SKUs per request
    MAX_PRODUCT_TAGS = 50                  # max tags per product
    MAX_VARIANT_OPTIONS = 3                # max options for variant
    
    # Request timeouts (seconds)
    TIMEOUT_HEALTH_CHECK = 5
    TIMEOUT_API_ENDPOINT = 30
    TIMEOUT_AI_HEAVY = 120
    TIMEOUT_WEBHOOK = 30
    
    # Rate/frequency
    MAX_CONCURRENT_UPLOADS = 5
    MIN_REQUEST_INTERVAL_MS = 100  # Minimum time between same endpoint calls


class AbuseProtectionError(HTTPException):
    """Raised when abuse limits are exceeded."""
    
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail=detail)


class PayloadValidator:
    """Validates request payloads for abuse patterns."""
    
    @staticmethod
    def validate_size(
        data: bytes,
        max_size: int = AbuseProtectionConfig.MAX_REQUEST_SIZE,
        name: str = "Request",
    ) -> None:
        """
        Validate payload size.
        
        Raises:
            AbuseProtectionError: If payload exceeds limit
        """
        size_mb = len(data) / (1024 * 1024)
        max_mb = max_size / (1024 * 1024)
        
        if len(data) > max_size:
            logger.warning(
                f"{name} exceeds size limit: {size_mb:.1f}MB > {max_mb:.1f}MB"
            )
            raise AbuseProtectionError(
                detail=f"{name} too large (max: {max_mb:.1f}MB)",
                status_code=413,
            )
    
    @staticmethod
    def validate_image_upload(
        file: UploadFile,
        max_size: int = AbuseProtectionConfig.MAX_IMAGE_SIZE,
    ) -> None:
        """
        Validate image upload.
        
        Checks:
        - File size
        - Image format (whitelist)
        """
        # Check file size
        if file.size and file.size > max_size:
            max_mb = max_size / (1024 * 1024)
            raise AbuseProtectionError(
                detail=f"Image too large (max: {max_mb:.1f}MB)",
                status_code=413,
            )
        
        # Check content type
        allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
        if file.content_type not in allowed_types:
            raise AbuseProtectionError(
                detail=f"Invalid image format. Allowed: JPEG, PNG, WebP, GIF",
                status_code=400,
            )
    
    @staticmethod
    def validate_sku_list(
        skus: List[str],
        max_length: int = AbuseProtectionConfig.MAX_SKU_LIST_LENGTH,
    ) -> None:
        """
        Validate SKU list for abuse.
        
        Checks:
        - Total count
        - Duplicate count
        - Individual SKU length
        """
        if len(skus) > max_length:
            raise AbuseProtectionError(
                detail=f"SKU list too long (max: {max_length})",
                status_code=400,
            )
        
        # Check for excessive duplicates (>50% duplicates = suspicious)
        unique_count = len(set(skus))
        duplicate_ratio = 1 - (unique_count / len(skus)) if skus else 0
        
        if duplicate_ratio > 0.5:
            logger.warning(f"Suspicious SKU list: {duplicate_ratio:.0%} duplicates")
            raise AbuseProtectionError(
                detail="Excessive duplicate SKUs detected",
                status_code=400,
            )
        
        # Check individual SKU length
        for sku in skus:
            if len(sku) > 255:
                raise AbuseProtectionError(
                    detail="SKU too long (max: 255 characters)",
                    status_code=400,
                )
            if len(sku) == 0:
                raise AbuseProtectionError(
                    detail="Empty SKU not allowed",
                    status_code=400,
                )
    
    @staticmethod
    def validate_text_length(
        text: str,
        max_length: int = AbuseProtectionConfig.MAX_AI_INPUT_LENGTH,
        field_name: str = "Input",
    ) -> None:
        """Validate text field length."""
        if len(text) > max_length:
            raise AbuseProtectionError(
                detail=f"{field_name} too long (max: {max_length} characters)",
                status_code=400,
            )
    
    @staticmethod
    def validate_array_length(
        items: List[Any],
        max_length: int,
        field_name: str = "Array",
    ) -> None:
        """Validate array/list length."""
        if len(items) > max_length:
            raise AbuseProtectionError(
                detail=f"{field_name} too long (max: {max_length} items)",
                status_code=400,
            )


class TimeoutGuard:
    """Decorator for enforcing request timeouts."""
    
    @staticmethod
    def timeout(seconds: float = AbuseProtectionConfig.TIMEOUT_API_ENDPOINT):
        """
        Decorator to enforce timeout on async functions.
        
        Usage:
            @TimeoutGuard.timeout(30)
            async def slow_operation():
                await asyncio.sleep(100)
                # Will raise TimeoutError after 30 seconds
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    return await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=seconds
                    )
                except asyncio.TimeoutError:
                    logger.error(
                        f"Timeout in {func.__name__} after {seconds}s",
                        extra={"function": func.__name__, "timeout": seconds}
                    )
                    raise AbuseProtectionError(
                        detail=f"Request timeout (exceeds {seconds}s limit)",
                        status_code=408,
                    )
            
            return wrapper
        
        return decorator
    
    @staticmethod
    def soft_timeout(
        seconds: float,
        fallback_fn: Callable = None,
    ):
        """
        Decorator for soft timeout (log warning but continue).
        
        Usage:
            @TimeoutGuard.soft_timeout(30, fallback_fn=return_cached)
            async def operation():
                ...
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    return await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=seconds
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        f"Soft timeout in {func.__name__}",
                        extra={"function": func.__name__, "timeout": seconds}
                    )
                    
                    if fallback_fn:
                        return await fallback_fn(*args, **kwargs) if asyncio.iscoroutinefunction(fallback_fn) else fallback_fn(*args, **kwargs)
                    
                    raise
            
            return wrapper
        
        return decorator


class InputSanitizer:
    """Sanitize and validate user inputs."""
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """
        Sanitize a string input.
        
        Removes:
        - Control characters
        - Excessive whitespace
        """
        if not isinstance(value, str):
            raise ValueError("Input must be string")
        
        if len(value) > max_length:
            raise ValueError(f"String too long (max: {max_length} chars)")
        
        # Remove null bytes and control characters
        value = ''.join(c for c in value if c.isprintable() or c.isspace())
        
        # Collapse multiple spaces
        value = ' '.join(value.split())
        
        return value.strip()
    
    @staticmethod
    def sanitize_list(items: List[str], max_items: int = 1000) -> List[str]:
        """Sanitize a list of strings."""
        if len(items) > max_items:
            raise ValueError(f"List too long (max: {max_items} items)")
        
        return [InputSanitizer.sanitize_string(item) for item in items]
    
    @staticmethod
    def is_suspicious_pattern(text: str) -> bool:
        """
        Detect suspicious patterns in text.
        
        Returns True if potentially malicious patterns are detected.
        """
        # SQL injection patterns
        sql_keywords = ["union", "select", "drop", "delete", "insert", "exec"]
        text_lower = text.lower()
        
        if any(f" {kw} " in f" {text_lower} " for kw in sql_keywords):
            return True
        
        # XXS patterns
        if any(p in text for p in ["<script", "javascript:", "onerror="]):
            return True
        
        # Excessive special characters (potential obfuscation)
        special_char_ratio = sum(1 for c in text if not c.isalnum() and not c.isspace()) / len(text) if text else 0
        if special_char_ratio > 0.5:
            return True
        
        return False


# Pydantic models with validation

class SKUListInput(BaseModel):
    """Validated SKU list input."""
    
    skus: List[str] = Field(
        ...,
        min_items=1,
        max_items=AbuseProtectionConfig.MAX_SKU_LIST_LENGTH,
        description="List of product SKUs",
    )
    
    @validator("skus")
    def validate_skus(cls, v):
        PayloadValidator.validate_sku_list(v)
        return v


class AIAnalysisInput(BaseModel):
    """Validated AI analysis input."""
    
    text: Optional[str] = Field(
        None,
        max_length=AbuseProtectionConfig.MAX_AI_INPUT_LENGTH,
        description="Text to analyze",
    )
    
    image_count: int = Field(
        default=0,
        le=AbuseProtectionConfig.MAX_AI_IMAGE_COUNT,
        description="Number of images to analyze",
    )
    
    @validator("text")
    def validate_text(cls, v):
        if v:
            PayloadValidator.validate_text_length(
                v,
                AbuseProtectionConfig.MAX_AI_INPUT_LENGTH,
            )
            if InputSanitizer.is_suspicious_pattern(v):
                raise ValueError("Input contains suspicious patterns")
        return v


class BatchProcessingInput(BaseModel):
    """Validated batch processing input."""
    
    items: List[Dict[str, Any]] = Field(
        ...,
        max_items=AbuseProtectionConfig.MAX_AI_BATCH_SIZE,
        description="Items to process",
    )
    
    @validator("items")
    def validate_items(cls, v):
        if len(v) > AbuseProtectionConfig.MAX_AI_BATCH_SIZE:
            raise ValueError(
                f"Batch too large (max: {AbuseProtectionConfig.MAX_AI_BATCH_SIZE})"
            )
        return v


# Usage helpers for endpoints

def check_abuse_limits(
    sku_list: List[str] = None,
    text: str = None,
    image_count: int = 0,
    payload_bytes: int = 0,
) -> None:
    """
    Check multiple abuse limits at once.
    
    Usage:
        check_abuse_limits(
            sku_list=skus,
            text=description,
            image_count=5,
            payload_bytes=len(request_body),
        )
    """
    if sku_list:
        PayloadValidator.validate_sku_list(sku_list)
    
    if text:
        PayloadValidator.validate_text_length(text)
    
    if image_count > AbuseProtectionConfig.MAX_AI_IMAGE_COUNT:
        raise AbuseProtectionError(
            detail=f"Too many images (max: {AbuseProtectionConfig.MAX_AI_IMAGE_COUNT})",
            status_code=400,
        )
    
    if payload_bytes > AbuseProtectionConfig.MAX_REQUEST_SIZE:
        raise AbuseProtectionError(
            detail="Payload too large",
            status_code=413,
        )
