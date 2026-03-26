"""
Production-grade Redis-backed rate limiting middleware.

Features:
- Per-shop rate limiting (primary)
- Per-IP fallback limiting
- Separate limits for endpoint categories:
  * Public API (generous)
  * Webhooks (moderate)
  * AI-heavy endpoints (strict)
- Returns HTTP 429 with Retry-After header
- Thread-safe, async-compatible
"""
import logging
from typing import Callable, Optional
from datetime import datetime
from functools import wraps
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import HTTPException
import os

try:
    import redis
    RedisError = redis.RedisError
except Exception:  # pragma: no cover - optional dependency
    redis = None

    class RedisError(Exception):
        pass

logger = logging.getLogger(__name__)

from app.core.redis_runtime import log_optional_redis_issue, redis_connection_kwargs


class RateLimitConfig:
    """Rate limiting configuration by endpoint category."""
    
    # Requests per minute by category
    PUBLIC_API_RPM = 300
    WEBHOOK_RPM = 120
    AI_HEAVY_RPM = 30
    IP_FALLBACK_RPM = 100
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv(
            "REDIS_URL", 
            "redis://localhost:6379/0"
        )
        self.ttl_seconds = 60  # Reset window per minute


class RateLimiter:
    """Redis-backed rate limiter for multi-tenant apps."""
    
    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        if redis is None:
            log_optional_redis_issue(logger, "Redis package not available. Rate limiting disabled.")
            self.redis_client = None
            return
        try:
            self.redis_client = redis.from_url(
                self.config.redis_url,
                **redis_connection_kwargs(),
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Redis rate limiter initialized successfully")
        except Exception as e:
            log_optional_redis_issue(logger, f"Failed to connect to Redis: {e}. Rate limiting disabled.")
            self.redis_client = None
    
    def _get_rate_limit(self, category: str) -> int:
        """Get RPM limit by category."""
        limits = {
            "public": self.config.PUBLIC_API_RPM,
            "webhook": self.config.WEBHOOK_RPM,
            "ai_heavy": self.config.AI_HEAVY_RPM,
        }
        return limits.get(category, self.config.PUBLIC_API_RPM)
    
    def _get_key_prefix(self, shop_id: Optional[str], ip: str) -> str:
        """Generate Redis key with timestamp for sliding window."""
        minute = int(datetime.utcnow().timestamp() / 60)
        
        if shop_id:
            return f"ratelimit:shop:{shop_id}:{minute}"
        else:
            return f"ratelimit:ip:{ip}:{minute}"
    
    async def check_limit(
        self,
        shop_id: Optional[str],
        ip: str,
        category: str = "public",
    ) -> tuple[bool, Optional[int]]:
        """
        Check if request is within rate limit.
        
        Returns:
            (within_limit, seconds_until_reset)
        """
        if not self.redis_client:
            # Redis unavailable: fail open (allow request)
            logger.debug("Redis unavailable, allowing request")
            return True, None
        
        try:
            limit = self._get_rate_limit(category)
            key = self._get_key_prefix(shop_id, ip)
            
            # Increment counter and get value
            current = self.redis_client.incr(key)
            
            # Set TTL on first request in window
            if current == 1:
                self.redis_client.expire(key, self.config.ttl_seconds)
            
            # Get remaining TTL for Retry-After header
            ttl = self.redis_client.ttl(key)
            if ttl == -1:
                self.redis_client.expire(key, self.config.ttl_seconds)
                ttl = self.config.ttl_seconds
            
            if current <= limit:
                return True, None
            else:
                return False, ttl
        
        except RedisError as e:
            logger.error(f"Redis error in rate limiter: {e}")
            # Fail open on Redis errors
            return True, None
    
    async def get_remaining(
        self,
        shop_id: Optional[str],
        ip: str,
        category: str = "public",
    ) -> int:
        """Get remaining requests in current window."""
        if not self.redis_client:
            return self._get_rate_limit(category)
        
        try:
            key = self._get_key_prefix(shop_id, ip)
            current = int(self.redis_client.get(key) or 0)
            limit = self._get_rate_limit(category)
            return max(0, limit - current)
        except Exception as e:
            logger.error(f"Error getting remaining requests: {e}")
            return self._get_rate_limit(category)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.
    
    Usage:
        app.add_middleware(RateLimitMiddleware, limiter=limiter)
    """
    
    # Endpoint category mappings
    WEBHOOK_PATHS = {"/webhooks", "/api/webhooks"}
    AI_HEAVY_PATHS = {"/analyze", "/ai/predict", "/api/ai"}
    
    def __init__(self, app, limiter: RateLimiter = None):
        super().__init__(app)
        self.limiter = limiter or RateLimiter()
    
    def _get_shop_id(self, request: Request) -> Optional[str]:
        """Extract shop_id from request (header or path param)."""
        # Try header first (Shopify standard)
        shop_id = request.headers.get("X-Shop-ID")
        if shop_id:
            return shop_id
        
        # Try query param
        shop_id = request.query_params.get("shop_id")
        if shop_id:
            return shop_id
        
        # Try path param (shop/{shop_id}/...)
        path_parts = request.url.path.split("/")
        if "shop" in path_parts:
            idx = path_parts.index("shop")
            if idx + 1 < len(path_parts):
                return path_parts[idx + 1]
        
        return None
    
    def _get_category(self, request: Request) -> str:
        """Determine rate limit category from request path."""
        path = request.url.path.lower()
        
        if any(path.startswith(p) for p in self.WEBHOOK_PATHS):
            return "webhook"
        
        if any(p in path for p in self.AI_HEAVY_PATHS):
            return "ai_heavy"
        
        return "public"
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, respecting X-Forwarded-For for proxies."""
        # Check X-Forwarded-For (for proxies/load balancers)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take first IP in chain
            return forwarded.split(",")[0].strip()
        
        # Check X-Real-IP (for reverse proxies)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to connection IP
        return request.client.host if request.client else "unknown"
    
    async def dispatch(self, request: Request, call_next):
        """Check rate limit before passing request."""
        # Extract context
        shop_id = self._get_shop_id(request)
        ip = self._get_client_ip(request)
        category = self._get_category(request)
        
        # Check rate limit
        within_limit, ttl = await self.limiter.check_limit(shop_id, ip, category)
        
        if not within_limit:
            logger.warning(
                f"Rate limit exceeded - shop:{shop_id} ip:{ip} category:{category}"
            )
            
            headers = {}
            if ttl:
                headers["Retry-After"] = str(ttl)
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too many requests",
                    "code": "RATE_LIMIT_EXCEEDED",
                    "retry_after_seconds": ttl or 60,
                },
                headers=headers,
            )
        
        # Add rate limit info to request state
        remaining = await self.limiter.get_remaining(shop_id, ip, category)
        request.state.rate_limit_remaining = remaining
        request.state.shop_id = shop_id
        
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(
            self.limiter._get_rate_limit(category)
        )
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response


def rate_limit(category: str = "public"):
    """
    Decorator for function-level rate limiting.
    
    Usage:
        @rate_limit("ai_heavy")
        async def analyze_endpoint(request: Request):
            ...
    """
    limiter = RateLimiter()
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            shop_id = request.headers.get("X-Shop-ID")
            ip = request.client.host if request.client else "unknown"
            
            within_limit, ttl = await limiter.check_limit(shop_id, ip, category)
            
            if not within_limit:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Too many requests",
                        "code": "RATE_LIMIT_EXCEEDED",
                        "retry_after_seconds": ttl or 60,
                    },
                    headers={"Retry-After": str(ttl or 60)},
                )
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    
    return decorator
