from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

from app.core.security import make_idempotency_key_for_webhook, verify_webhook_hmac
from app.services.webhook_queue import (
    WebhookQueueUnavailable,
    DuplicateWebhookDelivery,
    reserve_delivery,
    release_delivery,
    enqueue_webhook_delivery,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _get_redis(request: Request):
    return getattr(request.app.state, "redis", None)


def _get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


async def _enqueue_delivery(request: Request, topic: str, body: bytes) -> dict:
    redis_conn = _get_redis(request)
    delivery_key = make_idempotency_key_for_webhook(request.headers, body)

    try:
        reserve_delivery(redis_conn, delivery_key)
    except DuplicateWebhookDelivery:
        return {"status": "duplicate"}
    except WebhookQueueUnavailable as exc:
        raise HTTPException(status_code=503, detail="webhook_queue_unavailable") from exc

    headers = dict(request.headers)
    shop = headers.get("x-shopify-shop-domain")
    try:
        enqueue_webhook_delivery(
            redis_conn,
            delivery_key,
            topic,
            shop or "",
            body,
            headers,
            _get_request_id(request),
        )
    except WebhookQueueUnavailable as exc:
        release_delivery(redis_conn, delivery_key)
        raise HTTPException(status_code=503, detail="webhook_queue_unavailable") from exc

    return {"status": "accepted"}


@router.post("/app-uninstalled")
async def app_uninstalled(request: Request, x_shopify_hmac_sha256: str | None = Header(None)) -> Any:
    body = await request.body()
    verify_webhook_hmac(body, x_shopify_hmac_sha256)

    # Perform cleanup asynchronously with retries
    shop = request.headers.get("x-shopify-shop-domain")
    if not shop:
        raise HTTPException(status_code=400, detail="missing_shop_header")

    result = await _enqueue_delivery(request, "app/uninstalled", body)
    return result


@router.post("/gdpr/data_request")
async def gdpr_data_request(request: Request, x_shopify_hmac_sha256: str | None = Header(None)) -> Any:
    body = await request.body()
    verify_webhook_hmac(body, x_shopify_hmac_sha256)
    shop = request.headers.get("x-shopify-shop-domain")
    if not shop:
        raise HTTPException(status_code=400, detail="missing_shop_header")

    topic = request.headers.get("x-shopify-topic", "customers/data_request")
    result = await _enqueue_delivery(request, topic, body)
    if result.get("status") == "accepted":
        logger.info("Queued GDPR data_request for %s", shop)
    return result


@router.post("/gdpr/redact")
async def gdpr_redact(request: Request, x_shopify_hmac_sha256: str | None = Header(None)) -> Any:
    body = await request.body()
    verify_webhook_hmac(body, x_shopify_hmac_sha256)
    shop = request.headers.get("x-shopify-shop-domain")
    if not shop:
        raise HTTPException(status_code=400, detail="missing_shop_header")

    topic = request.headers.get("x-shopify-topic", "customers/redact")
    result = await _enqueue_delivery(request, topic, body)
    return result


@router.post("/customers/data_request")
async def customers_data_request(request: Request, x_shopify_hmac_sha256: str | None = Header(None)):
    body = await request.body()
    verify_webhook_hmac(body, x_shopify_hmac_sha256)
    return await gdpr_data_request(request, x_shopify_hmac_sha256)


@router.post("/customers/redact")
async def customers_redact(request: Request, x_shopify_hmac_sha256: str | None = Header(None)):
    body = await request.body()
    verify_webhook_hmac(body, x_shopify_hmac_sha256)
    return await gdpr_redact(request, x_shopify_hmac_sha256)


@router.post("/shop/redact")
async def shop_redact(request: Request, x_shopify_hmac_sha256: str | None = Header(None)):
    body = await request.body()
    verify_webhook_hmac(body, x_shopify_hmac_sha256)
    return await gdpr_redact(request, x_shopify_hmac_sha256)
@router.post("/webhooks/customers/data_request")
async def customer_data_request(request: Request):
    payload = await request.json()
    return {"status": "ok"}

@router.post("/webhooks/customers/redact")
async def customer_redact(request: Request):
    payload = await request.json()
    return {"status": "ok"}

@router.post("/webhooks/shop/redact")
async def shop_redact(request: Request):
    payload = await request.json()
    return {"status": "ok"}
