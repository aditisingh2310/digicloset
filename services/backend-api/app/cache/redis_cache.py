"""Cache service for try-on results using Redis"""

import logging
import hashlib
import json
from typing import Optional
import os
import redis

logger = logging.getLogger(__name__)


class CacheService:
    """Manages Redis caching for try-on results"""
    
    # Cache TTL: 24 hours
    CACHE_TTL = 86400  # seconds
    CACHE_KEY_PREFIX = "tryon_cache"
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize Redis connection"""
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            # Parse Redis URL
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            self.client.ping()
            logger.info("Cache service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None
    
    def _generate_hash(self, user_image_url: str, garment_image_url: str) -> str:
        """Generate cache key hash from image URLs"""
        content = f"{user_image_url}|{garment_image_url}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get_cached_result(
        self, 
        user_image_url: str, 
        garment_image_url: str
    ) -> Optional[dict]:
        """
        Retrieve cached try-on result if exists
        
        Args:
            user_image_url: URL of user's image
            garment_image_url: URL of garment image
            
        Returns:
            Dictionary with {image_url, generated_at} or None
        """
        if not self.client:
            return None
        
        try:
            cache_hash = self._generate_hash(user_image_url, garment_image_url)
            cache_key = f"{self.CACHE_KEY_PREFIX}:{cache_hash}"
            
            cached = self.client.get(cache_key)
            if cached:
                logger.info(f"Cache hit for {cache_hash}")
                return json.loads(cached)
            
            logger.debug(f"Cache miss for {cache_hash}")
            return None
            
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
            return None
    
    def set_cached_result(
        self,
        user_image_url: str,
        garment_image_url: str,
        image_url: str,
        ttl: int = CACHE_TTL
    ) -> bool:
        """
        Cache a try-on result
        
        Args:
            user_image_url: URL of user's image
            garment_image_url: URL of garment image
            image_url: URL of generated result image
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
        
        try:
            cache_hash = self._generate_hash(user_image_url, garment_image_url)
            cache_key = f"{self.CACHE_KEY_PREFIX}:{cache_hash}"
            
            cache_data = {
                "image_url": image_url,
                "generated_at": str(__import__('datetime').datetime.utcnow().isoformat()),
                "hash": cache_hash
            }
            
            self.client.setex(
                cache_key,
                ttl,
                json.dumps(cache_data)
            )
            
            logger.info(f"Cached result for {cache_hash}")
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete_cache(self, user_image_url: str, garment_image_url: str) -> bool:
        """Delete a cached result"""
        if not self.client:
            return False
        
        try:
            cache_hash = self._generate_hash(user_image_url, garment_image_url)
            cache_key = f"{self.CACHE_KEY_PREFIX}:{cache_hash}"
            
            self.client.delete(cache_key)
            logger.info(f"Deleted cache for {cache_hash}")
            return True
            
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def invalidate_all(self) -> bool:
        """Invalidate all cached results (careful!)"""
        if not self.client:
            return False
        
        try:
            pattern = f"{self.CACHE_KEY_PREFIX}:*"
            keys = self.client.keys(pattern)
            
            if keys:
                self.client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache entries")
            
            return True
            
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            return False


# Global cache instance
_cache_service = None


def get_cache_service() -> CacheService:
    """Get or create cache service singleton"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
