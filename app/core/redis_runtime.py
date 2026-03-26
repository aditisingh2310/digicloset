from __future__ import annotations

import logging
import os
from typing import Any, Dict

from app.core.config import settings


def redis_connection_kwargs(*, decode_responses: bool = True) -> Dict[str, Any]:
    """Shared Redis connection settings for fast local failure and consistent behavior."""
    return {
        "decode_responses": decode_responses,
        "socket_connect_timeout": float(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "0.2")),
        "socket_timeout": float(os.getenv("REDIS_SOCKET_TIMEOUT", "0.2")),
        "socket_keepalive": True,
        "health_check_interval": 10,
    }


def log_optional_redis_issue(logger: logging.Logger, message: str) -> None:
    """Only emit warning-level noise when Redis is actually required."""
    if settings.redis_required:
        logger.warning(message)
    else:
        logger.debug(message)
