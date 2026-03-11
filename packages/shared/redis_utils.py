"""
Redis connection and utilities.
Shared across all services for caching, sessions, and message queues.
"""

import redis
import logging
from typing import Optional, Any
from functools import wraps
import json

logger = logging.getLogger(__name__)

# Global Redis connection
_redis_client: Optional[redis.Redis] = None


def get_redis_connection(redis_url: Optional[str] = None) -> redis.Redis:
    """
    Get or create Redis connection.

    Args:
        redis_url: Redis connection URL. If None, uses REDIS_URL env var.

    Returns:
        Redis client instance
    """
    global _redis_client

    if _redis_client is not None:
        return _redis_client

    if redis_url is None:
        from .config import config
        redis_url = config.REDIS_URL

    try:
        _redis_client = redis.from_url(redis_url, decode_responses=True)
        # Test connection
        _redis_client.ping()
        logger.info("Redis connection established")
        return _redis_client
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise


def cache_key(*args: str, namespace: str = "cache") -> str:
    """Generate a cache key from arguments."""
    return f"{namespace}:{':'.join(str(arg) for arg in args)}"


def cache_result(ttl: int = 3600, namespace: str = "cache"):
    """
    Decorator to cache function results in Redis.

    Args:
        ttl: Time-to-live in seconds
        namespace: Cache namespace
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            redis_conn = get_redis_connection()
            key = cache_key(func.__name__, *args, namespace=namespace)

            # Try to get from cache
            cached = redis_conn.get(key)
            if cached:
                logger.debug(f"Cache hit: {key}")
                return json.loads(cached)

            # Call function and cache result
            result = await func(*args, **kwargs)
            redis_conn.setex(key, ttl, json.dumps(result, default=str))
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            redis_conn = get_redis_connection()
            key = cache_key(func.__name__, *args, namespace=namespace)

            # Try to get from cache
            cached = redis_conn.get(key)
            if cached:
                logger.debug(f"Cache hit: {key}")
                return json.loads(cached)

            # Call function and cache result
            result = func(*args, **kwargs)
            redis_conn.setex(key, ttl, json.dumps(result, default=str))
            return result

        # Return appropriate wrapper
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def invalidate_cache(key: str, namespace: str = "cache") -> None:
    """Invalidate a cache entry."""
    redis_conn = get_redis_connection()
    full_key = cache_key(key, namespace=namespace) if ':' not in key else key
    redis_conn.delete(full_key)
    logger.debug(f"Cache invalidated: {full_key}")


def close_redis() -> None:
    """Close Redis connection."""
    global _redis_client
    if _redis_client:
        _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")
