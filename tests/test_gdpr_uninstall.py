import base64
import hmac
import hashlib

from app.core.config import settings


def make_hmac(body: bytes) -> str:
    return base64.b64encode(hmac.new(settings.shopify_api_secret.encode(), body, hashlib.sha256).digest()).decode()


def test_gdpr_data_request_and_uninstall(client, monkeypatch):
    def fake_enqueue(redis_conn, delivery_key, topic, shop_domain, body, headers, request_id):
        return {"job_id": "job-1", "status": "queued"}

    monkeypatch.setattr("app.api.webhooks.enqueue_webhook_delivery", fake_enqueue)

    body = b'{"request":"data"}'
    sig = make_hmac(body)
    headers = {"X-Shopify-Hmac-Sha256": sig, "X-Shopify-Shop-Domain": "gdpr.myshopify.com"}

    # GDPR data_request
    r = client.post("/api/webhooks/customers/data_request", content=body, headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] in ("accepted", "duplicate")

    # Uninstall
    r2 = client.post("/api/webhooks/app-uninstalled", content=b'{}', headers={"X-Shopify-Hmac-Sha256": make_hmac(b'{}'), "X-Shopify-Shop-Domain": "gdpr.myshopify.com"})
    assert r2.status_code == 200
    assert r2.json()["status"] in ("accepted", "duplicate")


def test_webhook_no_shop_header_is_accepted(client, monkeypatch):
    def fake_enqueue(redis_conn, delivery_key, topic, shop_domain, body, headers, request_id):
        return {"job_id": "job-2", "status": "accepted"}

    monkeypatch.setattr("app.api.webhooks.enqueue_webhook_delivery", fake_enqueue)

    body = b'{"request":"data"}'
    sig = make_hmac(body)

    r = client.post("/api/webhooks/customers/data_request", content=body, headers={"X-Shopify-Hmac-Sha256": sig})
    assert r.status_code == 200
    assert r.json()["status"] in ("accepted", "duplicate")
