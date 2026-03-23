import base64
import hmac
import hashlib


def test_uninstall_webhook_cleanup(client, monkeypatch):
    called = {"topic": None}

    def fake_enqueue(redis_conn, delivery_key, topic, shop_domain, body, headers, request_id):
        called["topic"] = topic
        return {"job_id": "job-1", "status": "queued"}

    monkeypatch.setattr("app.api.webhooks.enqueue_webhook_delivery", fake_enqueue)

    body = b'{"foo":"bar"}'

    # Compute HMAC using configured secret
    from app.core.config import settings
    signature = base64.b64encode(hmac.new(settings.shopify_api_secret.encode(), body, hashlib.sha256).digest()).decode()

    res = client.post(
        "/api/webhooks/app-uninstalled",
        content=body,
        headers={
            "X-Shopify-Hmac-Sha256": signature,
            "X-Shopify-Shop-Domain": "a.myshopify.com",
            "X-Shopify-Delivery": "delivery-1",
        },
    )
    assert res.status_code == 200
    assert res.json().get("status") in ("accepted", "duplicate")
    assert called["topic"] == "app/uninstalled"
