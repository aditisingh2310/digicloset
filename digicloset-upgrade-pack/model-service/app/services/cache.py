"""
In-memory LRU cache for AI inference results.
Caches embedding vectors and color extraction results keyed by image hash (SHA-256).
Provides a Redis-ready upgrade path via environment toggle.
"""

import os
import time
import logging
from collections import OrderedDict
from threading import Lock

logger = logging.getLogger(__name__)

CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "500"))
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))  # 1 hour default


class LRUCache:
    """
    Thread-safe LRU cache with TTL support.
    Used to avoid redundant ML inference on duplicate or recently-seen images.
    """

    def __init__(self, max_size: int = CACHE_MAX_SIZE, ttl_seconds: int = CACHE_TTL_SECONDS):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, tuple] = OrderedDict()  # key -> (value, timestamp)
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str):
        """
        Retrieve a cached value by key.
        Returns None on miss or if TTL has expired.
        """
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                # Check TTL
                if time.time() - timestamp > self.ttl_seconds:
                    del self._cache[key]
                    self._misses += 1
                    return None
                # Move to end (most recently used)
                self._cache.move_to_end(key)
                self._hits += 1
                return value
            self._misses += 1
            return None

    def put(self, key: str, value):
        """Store a value in the cache, evicting the oldest entry if full."""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = (value, time.time())
            else:
                if len(self._cache) >= self.max_size:
                    evicted_key, _ = self._cache.popitem(last=False)
                    logger.debug(f"Cache evicted: {evicted_key[:16]}...")
                self._cache[key] = (value, time.time())

    @property
    def stats(self) -> dict:
        """Returns cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total, 3) if total > 0 else 0.0,
            }
    def clear(self):
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0


# ── Global Cache Instances ──
embedding_cache = LRUCache()
color_cache = LRUCache(max_size=200, ttl_seconds=1800)
