"""
Security middleware for the DigiCloset backend.
Provides SSRF protection, input sanitization, file validation, and rate limiting.
"""

import os
import re
import logging
import ipaddress
from urllib.parse import urlparse
from functools import lru_cache

from fastapi import Request, HTTPException, UploadFile
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

ALLOWED_IMAGE_DOMAINS = [
    d.strip()
    for d in os.getenv("ALLOWED_IMAGE_DOMAINS", "").split(",")
    if d.strip()
]

# ──────────────────────────────────────────────
# SSRF Protection
# ──────────────────────────────────────────────

_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
]


def is_private_ip(hostname: str) -> bool:
    """Check if a hostname resolves to a private/internal IP."""
    try:
        import socket
        resolved = socket.getaddrinfo(hostname, None)
        for _, _, _, _, addr in resolved:
            ip = ipaddress.ip_address(addr[0])
            for net in _PRIVATE_NETWORKS:
                if ip in net:
                    return True
    except Exception:
        return True  # If we can't resolve, block it
    return False


def validate_image_url(url: str) -> bool:
    """
    Validates a user-supplied image URL against SSRF protections.
    Returns True if the URL is safe, raises HTTPException otherwise.
    """
    parsed = urlparse(url)

    # Only allow HTTPS
    if parsed.scheme not in ("https",):
        raise HTTPException(status_code=400, detail="Only HTTPS image URLs are allowed")

    # Check against domain allowlist (if configured)
    if ALLOWED_IMAGE_DOMAINS:
        if parsed.hostname not in ALLOWED_IMAGE_DOMAINS:
            raise HTTPException(
                status_code=400,
                detail=f"Domain '{parsed.hostname}' is not in the allowed image sources list"
            )

    # Block private/internal IPs
    if is_private_ip(parsed.hostname):
        raise HTTPException(status_code=400, detail="Image URLs pointing to internal networks are blocked")

    return True


# ──────────────────────────────────────────────
# File Upload Validation
# ──────────────────────────────────────────────

# Magic byte signatures for allowed image formats
_MAGIC_SIGNATURES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"RIFF": "image/webp",  # WebP starts with RIFF....WEBP
}


def validate_image_magic_bytes(file_bytes: bytes, filename: str) -> str:
    """
    Validates that the file content matches known image magic bytes.
    Returns the detected MIME type, or raises HTTPException.
    """
    for signature, mime_type in _MAGIC_SIGNATURES.items():
        if file_bytes[:len(signature)] == signature:
            # Extra check for WebP: bytes 8-12 must be 'WEBP'
            if signature == b"RIFF" and file_bytes[8:12] != b"WEBP":
                continue
            return mime_type

    raise HTTPException(
        status_code=400,
        detail=f"File '{filename}' does not contain valid image data (magic byte check failed)"
    )


def validate_file_extension(filename: str) -> str:
    """Validates the file extension is in the allowlist."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File extension '{ext}' is not allowed. Accepted: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
        )
    return ext


def validate_file_size(size: int) -> None:
    """Validates uploaded file size."""
    if size > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum allowed size is {MAX_UPLOAD_SIZE_MB}MB"
        )


# ──────────────────────────────────────────────
# Path Traversal Protection
# ──────────────────────────────────────────────

_PATH_TRAVERSAL_PATTERN = re.compile(r"(\.\.|[/\\])")


def sanitize_item_id(item_id: str) -> str:
    """
    Strips path traversal sequences from item IDs.
    Raises HTTPException if the ID contains suspicious characters.
    """
    if _PATH_TRAVERSAL_PATTERN.search(item_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid item ID: path traversal characters detected"
        )
    return item_id


# ──────────────────────────────────────────────
# Input Sanitization Middleware
# ──────────────────────────────────────────────

_DANGEROUS_CHARS = re.compile(r"[<>\"';]")


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that sanitizes query parameters by stripping potentially
    dangerous characters (XSS, injection attempts).
    """

    async def dispatch(self, request: Request, call_next):
        # Sanitize query parameters
        for key, value in request.query_params.items():
            if _DANGEROUS_CHARS.search(value):
                logger.warning(f"Suspicious query parameter detected: {key}={value}")
                return JSONResponse(
                    status_code=400,
                    content={"detail": f"Query parameter '{key}' contains forbidden characters"}
                )

        response = await call_next(request)
        return response
