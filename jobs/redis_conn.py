import os
import logging

logger = logging.getLogger(__name__)


def get_redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


def get_redis_connection(**kwargs):
    """Return a Redis connection if `redis` package available, otherwise return a lightweight in-memory stub.

    This is helpful for unit tests that do not install `redis`.
    """
    try:
        from redis import Redis

        url = get_redis_url()
        logger.info("Connecting to Redis at %s", url)
        return Redis.from_url(url, **kwargs)
    except Exception:
        # Provide a minimal in-memory stub compatible with used methods in tests
        class _DummyRedis:
            def __init__(self):
                self._d = {}
                self._h = {}
                self._s = {}

            def setex(self, key, ttl, val):
                self._d[key] = val

            def set(self, key, val):
                self._d[key] = val
                return True

            def get(self, key):
                return self._d.get(key)

            def setnx(self, key, val):
                if key in self._d:
                    return False
                self._d[key] = val
                return True

            def expire(self, key, ttl):
                return True

            def delete(self, *keys):
                for key in keys:
                    self._d.pop(key, None)
                    self._h.pop(key, None)
                    self._s.pop(key, None)
                return True

            def hset(self, key, mapping=None, **kwargs):
                data = mapping or {}
                data.update(kwargs)
                if key not in self._h:
                    self._h[key] = {}
                self._h[key].update(data)
                return True

            def hget(self, key, field):
                return self._h.get(key, {}).get(field)

            def hgetall(self, key):
                return self._h.get(key, {}).copy()

            def hincrby(self, key, field, amount=1):
                if key not in self._h:
                    self._h[key] = {}
                current = int(self._h[key].get(field, 0))
                self._h[key][field] = current + amount
                return self._h[key][field]

            def rpush(self, key, value):
                if key not in self._d or not isinstance(self._d[key], list):
                    self._d[key] = []
                self._d[key].append(value)
                return len(self._d[key])

            def lrange(self, key, start, end):
                data = self._d.get(key, [])
                if not isinstance(data, list):
                    return []
                if end == -1:
                    end = len(data)
                return data[start : end + 1]

            def sadd(self, key, *values):
                if key not in self._s:
                    self._s[key] = set()
                self._s[key].update(values)
                return len(values)

            def smembers(self, key):
                return self._s.get(key, set()).copy()

            def srem(self, key, *values):
                if key not in self._s:
                    return 0
                removed = 0
                for value in values:
                    if value in self._s[key]:
                        self._s[key].remove(value)
                        removed += 1
                return removed

            def ping(self):
                return True

            def close(self):
                return None

        logger.warning("redis package not available; using DummyRedis stub for tests")
        return _DummyRedis()
