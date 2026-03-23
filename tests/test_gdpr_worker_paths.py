import json

from app.db.models import SessionLocal, Shop
from jobs.webhook_tasks import process_webhook


def _seed_shop(shop_domain: str, access_token: str = "tok-123") -> Shop:
    db = SessionLocal()
    shop = db.query(Shop).filter(Shop.domain == shop_domain).first()
    if shop is None:
        shop = Shop(domain=shop_domain, access_token=access_token)
        db.add(shop)
    else:
        shop.access_token = access_token
        shop.uninstalled_at = None
    db.commit()
    db.refresh(shop)
    db.close()
    return shop


def _load_shop(shop_domain: str) -> Shop:
    db = SessionLocal()
    shop = db.query(Shop).filter(Shop.domain == shop_domain).first()
    if shop:
        db.expunge(shop)
    db.close()
    return shop


def test_customer_redact_records_audit_without_uninstalling_shop(client, monkeypatch):
    shop_domain = "customer-redact.myshopify.com"
    _seed_shop(shop_domain)
    monkeypatch.setattr("jobs.webhook_tasks.get_redis_connection", lambda **kwargs: client.app.state.redis)

    result = process_webhook(
        "delivery-customer-redact",
        "customers/redact",
        shop_domain,
        b'{"customer":{"id":123,"email":"person@example.com"}}',
        {},
        "req-customer-redact",
    )

    shop = _load_shop(shop_domain)
    assert result["status"] == "completed"
    assert result["audit"]["status"] == "completed_no_customer_records"
    assert shop.access_token == "tok-123"
    assert shop.uninstalled_at is None

    events = client.app.state.redis.lrange("gdpr:events", 0, -1)
    event = json.loads(events[-1])
    assert event["event_type"] == "customers/redact"
    assert event["shop_domain"] == shop_domain
    assert event["customer_email"] == "person@example.com"


def test_data_request_records_manual_review_event(client, monkeypatch):
    monkeypatch.setattr("jobs.webhook_tasks.get_redis_connection", lambda **kwargs: client.app.state.redis)

    result = process_webhook(
        "delivery-data-request",
        "customers/data_request",
        "data-request.myshopify.com",
        b'{"customer":{"id":456,"email":"export@example.com"}}',
        {},
        "req-data-request",
    )

    assert result["status"] == "completed"
    assert result["audit"]["status"] == "pending_review"
    assert result["audit"]["fulfillment_mode"] == "manual_review"

    events = client.app.state.redis.lrange("gdpr:events", 0, -1)
    event = json.loads(events[-1])
    assert event["event_type"] == "customers/data_request"
    assert event["customer_id"] == "456"
    assert event["customer_email"] == "export@example.com"


def test_shop_redact_still_removes_shop_data(client, monkeypatch):
    shop_domain = "shop-redact.myshopify.com"
    _seed_shop(shop_domain, access_token="shop-redact-token")
    monkeypatch.setattr("jobs.webhook_tasks.get_redis_connection", lambda **kwargs: client.app.state.redis)

    result = process_webhook(
        "delivery-shop-redact",
        "shop/redact",
        shop_domain,
        b'{"shop_id":789}',
        {},
        "req-shop-redact",
    )

    shop = _load_shop(shop_domain)
    assert result["status"] == "completed"
    assert shop.access_token == ""
    assert shop.uninstalled_at is not None
