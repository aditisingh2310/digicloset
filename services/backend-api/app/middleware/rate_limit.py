"""Rate limiting middleware using Redis"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import redis
import os

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter using Redis"""
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize Redis connection"""
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.requests_per_minute = 10
        self.key_prefix = "ratelimit"
        
        try:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            self.client.ping()
            logger.info("Rate limiter initialized")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None
    
    def _get_key(self, identifier: str) -> str:
        """Get Redis key for identifier"""
        return f"{self.key_prefix}:{identifier}"
    
    def is_allowed(self, identifier: str) -> tuple[bool, int]:
        """
        Check if request is allowed
        
        Args:
            identifier: User/session identifier
            
        Returns:
            Tuple of (allowed: bool, remaining_requests: int)
        """
        if not self.client:
            # If Redis not available, allow all requests
            return True, self.requests_per_minute
        
        try:
            key = self._get_key(identifier)
            current = self.client.get(key)
            
            if current is None:
                # First request
                self.client.setex(key, 60, 1)  # Expire in 60 seconds
                return True, self.requests_per_minute - 1
            
            current_count = int(current)
            
            if current_count >= self.requests_per_minute:
                return False, 0
            
            # Increment counter
            self.client.incr(key)
            remaining = self.requests_per_minute - current_count - 1
            
            return True, remaining
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # On error, allow request
            return True, self.requests_per_minute
    
    def reset(self, identifier: str) -> bool:
        """Reset rate limit for identifier"""
        if not self.client:
            return False
        
        try:
            key = self._get_key(identifier)
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")
            return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting"""
    
    def __init__(self, app, redis_url: Optional[str] = None):
        super().__init__(app)
        self.limiter = RateLimiter(redis_url)
        # Endpoints to rate limit
        self.rate_limited_paths = {
            "/api/v1/try-on/generate",
            "/api/v1/try-on/request"
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Rate limit request if applicable"""
        
        # Check if path should be rate limited
        if request.url.path not in self.rate_limited_paths:
            return await call_next(request)
        
        # Get identifier (shop ID or session ID)
        identifier = self._get_identifier(request)
        
        # Check rate limit
        allowed, remaining = self.limiter.is_allowed(identifier)
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for {identifier}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Too many requests",
                    "message": "Rate limit exceeded (10 requests per minute)"
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.limiter.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int((datetime.utcnow() + timedelta(seconds=60)).timestamp()))
        
        return response
    
    @staticmethod
    def _get_identifier(request: Request) -> str:
        """Extract identifier from request"""
        # Try to get shop ID from header
        shop_id = request.headers.get("X-Shop-ID")
        if shop_id:
            return shop_id
        
        # Try to get from query param
        shop_id = request.query_params.get("shop_id")
        if shop_id:
            return shop_id
        
        # Try to get from form data
        try:
            if hasattr(request, 'body'):
                import json
                body = json.loads(request.body())
                shop_id = body.get("shop_id")
                if shop_id:
                    return shop_id
        except:
            pass
        
        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"


# Global rate limiter instance
_rate_limiter = None


def get_rate_limiter(redis_url: Optional[str] = None) -> RateLimiter:
    """Get or create rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(redis_url)
    return _rate_limiter
