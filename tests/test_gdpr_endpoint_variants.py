import base64
import hashlib
import hmac

from app.core.config import settings


def _make_hmac(body: bytes) -> str:
    return base64.b64encode(
        hmac.new(settings.shopify_api_secret.encode(), body, hashlib.sha256).digest()
    ).decode()


def test_gdpr_data_request_alias_uses_topic_header(client, monkeypatch):
    called = {}

    def fake_enqueue(redis_conn, delivery_key, topic, shop_domain, body, headers, request_id):
        called["topic"] = topic
        called["shop_domain"] = shop_domain
        return {"job_id": "job-data-request", "status": "queued"}

    monkeypatch.setattr("app.api.webhooks.enqueue_webhook_delivery", fake_enqueue)

    body = b'{"customer":{"id":1}}'
    res = client.post(
        "/api/webhooks/gdpr/data_request",
        content=body,
        headers={
            "X-Shopify-Hmac-Sha256": _make_hmac(body),
            "X-Shopify-Shop-Domain": "alias-data-request.myshopify.com",
            "X-Shopify-Topic": "customers/data_request",
        },
    )

    assert res.status_code == 200
    assert called["topic"] == "customers/data_request"
    assert called["shop_domain"] == "alias-data-request.myshopify.com"


def test_gdpr_redact_alias_defaults_to_customer_redact(client, monkeypatch):
    called = {}

    def fake_enqueue(redis_conn, delivery_key, topic, shop_domain, body, headers, request_id):
        called["topic"] = topic
        return {"job_id": "job-customer-redact", "status": "queued"}

    monkeypatch.setattr("app.api.webhooks.enqueue_webhook_delivery", fake_enqueue)

    body = b'{"customer":{"id":2}}'
    res = client.post(
        "/api/webhooks/gdpr/redact",
        content=body,
        headers={
            "X-Shopify-Hmac-Sha256": _make_hmac(body),
            "X-Shopify-Shop-Domain": "alias-redact.myshopify.com",
        },
    )

    assert res.status_code == 200
    assert called["topic"] == "customers/redact"


def test_gdpr_redact_alias_can_forward_shop_redact_topic(client, monkeypatch):
    called = {}

    def fake_enqueue(redis_conn, delivery_key, topic, shop_domain, body, headers, request_id):
        called["topic"] = topic
        return {"job_id": "job-shop-redact", "status": "queued"}

    monkeypatch.setattr("app.api.webhooks.enqueue_webhook_delivery", fake_enqueue)

    body = b'{"shop_id":99}'
    res = client.post(
        "/api/webhooks/gdpr/redact",
        content=body,
        headers={
            "X-Shopify-Hmac-Sha256": _make_hmac(body),
            "X-Shopify-Shop-Domain": "alias-shop-redact.myshopify.com",
            "X-Shopify-Topic": "shop/redact",
        },
    )

    assert res.status_code == 200
    assert called["topic"] == "shop/redact"
