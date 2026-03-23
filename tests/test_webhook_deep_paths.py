import asyncio
import base64
import hashlib
import hmac
import json

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.core.security import make_idempotency_key_for_webhook
from app.services.billing_service import InMemoryStore
from app.models.billing import SubscriptionRecord, UsageRecord
from app.services.data_deletion import DataDeletionService
from app.services.webhook_queue import WebhookQueueUnavailable, _delivery_idempotency_key
from jobs.webhook_tasks import WEBHOOK_DLQ_KEY, process_webhook


def _make_hmac(body: bytes) -> str:
    return base64.b64encode(
        hmac.new(settings.shopify_api_secret.encode(), body, hashlib.sha256).digest()
    ).decode()


def test_webhook_wrapper_swallows_internal_http_exception(client, monkeypatch):
    async def fake_process(request, topic, body):
        raise HTTPException(status_code=418, detail="teapot")

    monkeypatch.setattr("app.api.webhooks._process_shopify_webhook", fake_process)

    body = b"{}"
    response = client.post(
        "/api/webhooks/customers/data_request",
        content=body,
        headers={
            "X-Shopify-Hmac-Sha256": _make_hmac(body),
            "X-Shopify-Shop-Domain": "deep-http-error.myshopify.com",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["message"] == "processing_skipped"
    assert payload["detail"] == "teapot"


def test_webhook_wrapper_swallows_unexpected_exception(client, monkeypatch):
    async def fake_process(request, topic, body):
        raise RuntimeError("worker exploded")

    monkeypatch.setattr("app.api.webhooks._process_shopify_webhook", fake_process)

    body = b"{}"
    response = client.post(
        "/api/webhooks/customers/redact",
        content=body,
        headers={
            "X-Shopify-Hmac-Sha256": _make_hmac(body),
            "X-Shopify-Shop-Domain": "deep-runtime-error.myshopify.com",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["message"] == "processing_skipped"
    assert payload["detail"] == "worker exploded"


def test_enqueue_failure_releases_delivery_reservation(client, monkeypatch):
    def fake_enqueue(*args, **kwargs):
        raise WebhookQueueUnavailable("queue down")

    monkeypatch.setattr("app.api.webhooks.enqueue_webhook_delivery", fake_enqueue)

    body = b'{"customer":{"id":9}}'
    headers = {
        "X-Shopify-Hmac-Sha256": _make_hmac(body),
        "X-Shopify-Shop-Domain": "release-check.myshopify.com",
        "X-Shopify-Delivery": "release-check-1",
    }

    first = client.post("/api/webhooks/customers/data_request", content=body, headers=headers)
    second = client.post("/api/webhooks/customers/data_request", content=body, headers=headers)

    assert first.status_code == 503
    assert second.status_code == 503

    delivery_key = _delivery_idempotency_key(make_idempotency_key_for_webhook(headers, body))
    assert client.app.state.redis.get(delivery_key) is None


def test_process_webhook_returns_duplicate_when_status_already_completed(client, monkeypatch):
    redis_conn = client.app.state.redis
    redis_conn.hset("webhook:delivery:already-done", mapping={"status": "completed"})
    monkeypatch.setattr("jobs.webhook_tasks.get_redis_connection", lambda **kwargs: redis_conn)

    result = process_webhook(
        "already-done",
        "customers/data_request",
        "duplicate-check.myshopify.com",
        b"{}",
        {},
        "req-duplicate-check",
    )

    assert result == {"status": "duplicate"}


def test_process_webhook_marks_unhandled_topics_completed(client, monkeypatch):
    redis_conn = client.app.state.redis
    monkeypatch.setattr("jobs.webhook_tasks.get_redis_connection", lambda **kwargs: redis_conn)

    result = process_webhook(
        "unknown-topic-delivery",
        "products/update",
        "unknown-topic.myshopify.com",
        b"{}",
        {},
        "req-unknown-topic",
    )

    assert result == {"status": "completed", "note": "unhandled topic"}
    assert redis_conn.hget("webhook:delivery:unknown-topic-delivery", "status") == "completed"


def test_process_webhook_records_dead_letter_on_terminal_failure(client, monkeypatch):
    redis_conn = client.app.state.redis
    monkeypatch.setattr("jobs.webhook_tasks.get_redis_connection", lambda **kwargs: redis_conn)
    monkeypatch.setattr(
        "jobs.webhook_tasks.record_data_request",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("dlq-me")),
    )

    with pytest.raises(RuntimeError, match="dlq-me"):
        process_webhook(
            "terminal-failure-delivery",
            "customers/data_request",
            "dead-letter.myshopify.com",
            b"{}",
            {},
            "req-terminal-failure",
        )

    events = redis_conn.lrange(WEBHOOK_DLQ_KEY, 0, -1)
    assert len(events) == 1
    payload = json.loads(events[0])
    assert payload["delivery_key"] == "terminal-failure-delivery"
    assert payload["topic"] == "customers/data_request"
    assert payload["error"] == "dlq-me"


def test_data_deletion_service_resets_inmemory_records():
    store = InMemoryStore()
    store.subs["store-delete.myshopify.com"] = SubscriptionRecord(
        shop_domain="store-delete.myshopify.com",
        status="active",
    )
    store.usage["store-delete.myshopify.com"] = UsageRecord(
        shop_domain="store-delete.myshopify.com",
        ai_calls_this_month=12,
        products_processed_this_month=4,
        month_period="2026-03",
    )

    audit = asyncio.run(
        DataDeletionService(store=store, redis=None).delete_shop_data("store-delete.myshopify.com")
    )

    assert audit.details["subscription_status"] == "uninstalled"
    assert audit.details["usage_reset"] is True
    assert store.subs["store-delete.myshopify.com"].status == "uninstalled"
    assert store.usage["store-delete.myshopify.com"].ai_calls_this_month == 0
    assert store.usage["store-delete.myshopify.com"].products_processed_this_month == 0
    assert store.usage["store-delete.myshopify.com"].month_period is None
