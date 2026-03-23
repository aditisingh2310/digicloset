import base64
import hashlib
import hmac

from app.core.config import settings


def _make_hmac(body: bytes) -> str:
    return base64.b64encode(
        hmac.new(settings.shopify_api_secret.encode(), body, hashlib.sha256).digest()
    ).decode()


def test_webhook_idempotent_duplicate(client, monkeypatch):
    def fake_enqueue(redis_conn, delivery_key, topic, shop_domain, body, headers, request_id):
        return {"job_id": "job-1", "status": "queued"}

    monkeypatch.setattr("app.api.webhooks.enqueue_webhook_delivery", fake_enqueue)

    body = b'{"foo":"bar"}'
    headers = {
        "X-Shopify-Hmac-Sha256": _make_hmac(body),
        "X-Shopify-Shop-Domain": "dup.myshopify.com",
        "X-Shopify-Delivery": "same-delivery",
    }

    first = client.post("/api/webhooks/app-uninstalled", content=body, headers=headers)
    second = client.post("/api/webhooks/app-uninstalled", content=body, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["status"] in ("accepted", "duplicate")
    assert second.json()["status"] == "duplicate"
