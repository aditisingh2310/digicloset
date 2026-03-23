import json

from app.db.models import SessionLocal, Shop
from jobs.webhook_tasks import process_webhook


def _seed_shop(shop_domain: str, access_token: str = "tok-123") -> None:
    db = SessionLocal()
    shop = db.query(Shop).filter(Shop.domain == shop_domain).first()
    if shop is None:
        shop = Shop(domain=shop_domain, access_token=access_token)
        db.add(shop)
    else:
        shop.access_token = access_token
        shop.uninstalled_at = None
    db.commit()
    db.close()


def _fetch_shop(shop_domain: str) -> Shop | None:
    db = SessionLocal()
    shop = db.query(Shop).filter(Shop.domain == shop_domain).first()
    if shop:
        db.expunge(shop)
    db.close()
    return shop


def _seed_sessions(redis_conn, shop_domain: str, session_id: str) -> None:
    redis_conn.setex(f"session:{session_id}", 3600, json.dumps({"shop": shop_domain}))
    redis_conn.setex(f"shopify_session:{session_id}", 3600, json.dumps({"shop": shop_domain}))
    redis_conn.setex(f"session_shop:{session_id}", 3600, shop_domain)
    redis_conn.sadd(f"shop_sessions:{shop_domain}", session_id)


def test_customer_redact_preserves_shop_sessions(client, monkeypatch):
    shop_domain = "customer-session-guard.myshopify.com"
    redis_conn = client.app.state.redis
    _seed_shop(shop_domain)
    _seed_sessions(redis_conn, shop_domain, "sess-customer-redact")
    monkeypatch.setattr("jobs.webhook_tasks.get_redis_connection", lambda **kwargs: redis_conn)

    result = process_webhook(
        "delivery-customer-session-guard",
        "customers/redact",
        shop_domain,
        b'{"customer":{"id":555,"email":"privacy@example.com"}}',
        {},
        "req-customer-session-guard",
    )

    shop = _fetch_shop(shop_domain)
    assert result["status"] == "completed"
    assert shop.access_token == "tok-123"
    assert shop.uninstalled_at is None
    assert redis_conn.get("session:sess-customer-redact") is not None
    assert "sess-customer-redact" in redis_conn.smembers(f"shop_sessions:{shop_domain}")


def test_shop_redact_revokes_shop_sessions(client, monkeypatch):
    shop_domain = "shop-session-guard.myshopify.com"
    redis_conn = client.app.state.redis
    _seed_shop(shop_domain, access_token="shop-redact-token")
    _seed_sessions(redis_conn, shop_domain, "sess-shop-redact")
    monkeypatch.setattr("jobs.webhook_tasks.get_redis_connection", lambda **kwargs: redis_conn)

    result = process_webhook(
        "delivery-shop-session-guard",
        "shop/redact",
        shop_domain,
        b'{"shop_id":777}',
        {},
        "req-shop-session-guard",
    )

    shop = _fetch_shop(shop_domain)
    assert result["status"] == "completed"
    assert shop.access_token == ""
    assert shop.uninstalled_at is not None
    assert redis_conn.get("session:sess-shop-redact") is None
    assert redis_conn.smembers(f"shop_sessions:{shop_domain}") == set()
    assert redis_conn.hget("webhook:delivery:delivery-shop-session-guard", "status") == "completed"


def test_data_request_records_invalid_json_body_without_crashing(client, monkeypatch):
    redis_conn = client.app.state.redis
    monkeypatch.setattr("jobs.webhook_tasks.get_redis_connection", lambda **kwargs: redis_conn)

    result = process_webhook(
        "delivery-invalid-data-request",
        "customers/data_request",
        "invalid-json.myshopify.com",
        b"raw-non-json-payload",
        {},
        "req-invalid-data-request",
    )

    assert result["status"] == "completed"
    assert result["audit"]["status"] == "pending_review"
    payload = json.loads(result["audit"]["payload_json"])
    assert payload["raw_body"] == "raw-non-json-payload"


def test_privacy_and_terms_routes_are_not_placeholder(client):
    privacy = client.get("/privacy")
    terms = client.get("/terms")

    assert privacy.status_code == 200
    assert terms.status_code == 200
    assert "Replace with your real policy" not in privacy.text
    assert "Replace with your real terms" not in terms.text
    assert "support@digicloset.ai" in privacy.text
