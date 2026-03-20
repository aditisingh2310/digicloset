from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

from app.core.config import settings
from app.core.security import (
    make_idempotency_key_for_webhook,
    verify_shopify_webhook,
)
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


def _safe_webhook_response(error_message: str, request_id: str | None = None) -> dict:
    # Shopify expects HTTP 200 for processed webhooks; we intentionally swallow internal errors.
    return {
        "status": "completed",
        "message": "processing_skipped",
        "detail": error_message,
        "request_id": request_id,
    }


async def _process_shopify_webhook(request: Request, topic: str, body: bytes) -> dict:
    # Verify signature with global helper and place in background queue.
    hmac_header = request.headers.get("x-shopify-hmac-sha256")
    verify_shopify_webhook(body, hmac_header, settings.shopify_api_secret)

    shop = request.headers.get("x-shopify-shop-domain", "")
    if not shop:
        logger.warning("Shop header missing for webhook topic %s", topic)

    logger.info(
        "Received Shopify webhook topic=%s shop=%s delivery=%s",
        topic,
        shop or "unknown",
        request.headers.get("x-shopify-delivery") or request.headers.get("x-shopify-delivery-id"),
    )

    result = await _enqueue_delivery(request, topic, body)
    return result


async def _webhook_wrapper(func, request: Request, *args, **kwargs):
    request_id = _get_request_id(request)
    try:
        return await func(request, *args, **kwargs)
    except HTTPException as http_exc:
        if http_exc.status_code == 401:
            logger.warning("Unauthorized Shopify webhook request: %s", http_exc.detail)
            raise
        logger.exception("Shopify webhook HTTP exception: %s", http_exc)
        return _safe_webhook_response(str(http_exc.detail), request_id)
    except Exception as exc:
        logger.exception("Shopify webhook processing exception", exc_info=exc)
        return _safe_webhook_response(str(exc), request_id)


@router.post("/app-uninstalled")
async def app_uninstalled(request: Request) -> Any:
    body = await request.body()
    return await _webhook_wrapper(_process_shopify_webhook, request, "app/uninstalled", body)


@router.post("/gdpr/data_request")
async def gdpr_data_request(request: Request) -> Any:
    body = await request.body()
    shop = request.headers.get("x-shopify-shop-domain", "")
    logger.info("GDPR data_request webhook from shop %s", shop or "unknown")
    return await _webhook_wrapper(_process_shopify_webhook, request, request.headers.get("x-shopify-topic", "customers/data_request"), body)


@router.post("/gdpr/redact")
async def gdpr_redact(request: Request) -> Any:
    body = await request.body()
    shop = request.headers.get("x-shopify-shop-domain", "")
    logger.info("GDPR redact webhook from shop %s", shop or "unknown")
    return await _webhook_wrapper(_process_shopify_webhook, request, request.headers.get("x-shopify-topic", "customers/redact"), body)


@router.post("/customers/data_request")
async def customers_data_request(request: Request):
    body = await request.body()
    return await _webhook_wrapper(_process_shopify_webhook, request, "customers/data_request", body)


@router.post("/customers/redact")
async def customers_redact(request: Request):
    body = await request.body()
    return await _webhook_wrapper(_process_shopify_webhook, request, "customers/redact", body)


@router.post("/shop/redact")
async def shop_redact(request: Request):
    body = await request.body()
    return await _webhook_wrapper(_process_shopify_webhook, request, "shop/redact", body)
