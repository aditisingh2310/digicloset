from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings


def test_health_endpoint_returns_ok():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_ready_is_public():
    client = TestClient(app)
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    payload = resp.json()
    assert "ready" in payload
    assert "missing" in payload


def test_docs_is_public():
    client = TestClient(app)
    resp = client.get("/docs")
    assert resp.status_code == 200
    assert "Swagger UI" in resp.text


def test_openapi_is_public():
    client = TestClient(app)
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    assert resp.json()["openapi"].startswith("3.")


def test_health_reports_optional_redis_as_ok(monkeypatch):
    client = TestClient(app)
    previous_redis = getattr(app.state, "redis", None)
    monkeypatch.setattr(settings, "redis_required", False, raising=False)
    app.state.redis = None

    resp = client.get("/health")

    app.state.redis = previous_redis
    assert resp.status_code == 200
    assert resp.json() == {
        "status": "ok",
        "details": {
            "ai_service": True,
            "redis": False,
            "redis_required": False,
        },
    }


def test_health_requires_redis_when_enabled(monkeypatch):
    client = TestClient(app)
    previous_redis = getattr(app.state, "redis", None)
    monkeypatch.setattr(settings, "redis_required", True, raising=False)
    app.state.redis = None

    resp = client.get("/health")

    app.state.redis = previous_redis
    assert resp.status_code == 200
    assert resp.json() == {
        "status": "unhealthy",
        "details": {
            "ai_service": True,
            "redis": False,
            "redis_required": True,
        },
    }
