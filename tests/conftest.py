import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure project root is on path so `import app` works
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.main import app


class DummyRedis:
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


@pytest.fixture(autouse=True)
def inject_redis():
    app.state.redis = DummyRedis()
    try:
        from app.services.billing_service import InMemoryStore
        from app.models.billing import SubscriptionRecord
        from datetime import datetime, timedelta

        app.state.store = InMemoryStore()
        # Seed trial subscriptions for common test tenants
        for shop in ("a.myshopify.com", "b.myshopify.com"):
            app.state.store.subs[shop] = SubscriptionRecord(
                shop_domain=shop,
                status="pending",
                trial_ends_at=datetime.utcnow() + timedelta(days=7),
            )
    except Exception:
        app.state.store = None
    yield


@pytest.fixture
def client(inject_redis):
    return TestClient(app)


@pytest.fixture
def mock_ai_service(monkeypatch):
    class MockAIService:
        async def infer(self, prompt, max_tokens=128, timeout=10.0):
            return {"text": f"echo: {prompt}", "confidence": 0.99, "model": "mock-model"}

    # Attach to app state for tests
    app.state.ai_service = MockAIService()
    return app.state.ai_service


@pytest.fixture
def tenant_headers_a():
    return {"x-shopify-shop-domain": "a.myshopify.com", "authorization": "Bearer tokA"}


@pytest.fixture
def tenant_headers_b():
    return {"x-shopify-shop-domain": "b.myshopify.com", "authorization": "Bearer tokB"}
