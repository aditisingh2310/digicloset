import base64
import hashlib
import hmac

from app.core.config import settings
from app.services.webhook_queue import WebhookQueueUnavailable


def test_webhook_queue_unavailable_returns_503(client, monkeypatch):
    def fake_enqueue(*args, **kwargs):
        raise WebhookQueueUnavailable("queue down")

    monkeypatch.setattr("app.api.webhooks.enqueue_webhook_delivery", fake_enqueue)

    body = b"{}"
    signature = base64.b64encode(
        hmac.new(settings.shopify_api_secret.encode(), body, hashlib.sha256).digest()
    ).decode()

    res = client.post(
        "/api/webhooks/app-uninstalled",
        data=body,
        headers={
            "X-Shopify-Hmac-Sha256": signature,
            "X-Shopify-Shop-Domain": "down.myshopify.com",
        },
    )

    assert res.status_code == 503
    payload = res.json()
    assert payload.get("error") == "webhook_queue_unavailable"
    assert payload.get("status") == 503
