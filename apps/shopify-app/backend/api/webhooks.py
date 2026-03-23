from fastapi import APIRouter, Request, HTTPException
import hmac
import hashlib
import base64
import os
import json
from typing import Dict, Any

router = APIRouter()

SHOPIFY_WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET")


# ---------------------------------------------------
# 🔐 HMAC Verification
# ---------------------------------------------------
def verify_webhook_hmac(raw_body: bytes, hmac_header: str) -> None:
    if not hmac_header:
        raise HTTPException(status_code=401, detail="Missing HMAC header")

    digest = hmac.new(
        SHOPIFY_WEBHOOK_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).digest()

    computed_hmac = base64.b64encode(digest).decode()

    if not hmac.compare_digest(computed_hmac, hmac_header):
        raise HTTPException(status_code=401, detail="Invalid HMAC")


# ---------------------------------------------------
# 🚀 Queue Stub (replace with your Redis queue)
# ---------------------------------------------------
async def enqueue_webhook(topic: str, shop: str, payload: Dict[str, Any]):
    """
    Replace this with your real queue logic (Redis, Celery, etc.)
    """
    print(f"[WEBHOOK QUEUED] {topic} from {shop}")
    # Example:
    # await redis_queue.enqueue(topic, shop, payload)


# ---------------------------------------------------
# 📦 Shared Handler
# ---------------------------------------------------
async def process_webhook(request: Request, topic: str):
    raw_body = await request.body()

    hmac_header = request.headers.get("x-shopify-hmac-sha256")
    shop = request.headers.get("x-shopify-shop-domain")

    # Verify webhook authenticity
    verify_webhook_hmac(raw_body, hmac_header)

    try:
        payload = json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Enqueue for async processing
    await enqueue_webhook(topic, shop, payload)

    return {"status": "ok"}
# ---------------------------------------------------

@router.post("/webhooks/app/uninstalled")
async def app_uninstalled(request: Request):
    return await process_webhook(request, "app/uninstalled")


@router.post("/webhooks/customers/data_request")
async def customers_data_request(request: Request):
    return await process_webhook(request, "customers/data_request")


@router.post("/webhooks/customers/redact")
async def customers_redact(request: Request):
    return await process_webhook(request, "customers/redact")


@router.post("/webhooks/shop/redact")
async def shop_redact(request: Request):
    return await process_webhook(request, "shop/redact")
