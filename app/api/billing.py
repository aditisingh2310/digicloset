from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel, Field

from app.services.billing_service import BillingService, InMemoryStore
from app.core.plans import PLANS
from app.core.security import verify_webhook_hmac

router = APIRouter(prefix="/billing", tags=["billing"])


class BillingActivateRequest(BaseModel):
    shop: str = Field(..., min_length=3)
    charge_id: str = Field(..., min_length=1)


class BillingWebhookPayload(BaseModel):
    topic: str = Field(..., min_length=3)


def _store_for_app(request: Request):
    return getattr(request.app.state, "store", InMemoryStore())


@router.post("/create")
async def create_charge(request: Request):
    tenant = getattr(request.state, "tenant", None)
    if not tenant:
        raise HTTPException(status_code=401, detail="Missing tenant")

    svc = BillingService(tenant.shop_domain, tenant.access_token, _store_for_app(request))
    return await svc.create_recurring_charge("starter")


@router.post("/activate")
async def activate_charge(payload: BillingActivateRequest, request: Request):
    svc = BillingService(payload.shop, "", _store_for_app(request))
    rec = await svc.activate_charge(payload.charge_id)
    return {"status": "activated", "subscription": rec.dict()}


@router.post("/webhook")
async def billing_webhook(
    request: Request,
    x_shopify_hmac_sha256: Optional[str] = Header(None),
):
    body = await request.body()
    verify_webhook_hmac(body, x_shopify_hmac_sha256)

    payload = BillingWebhookPayload.model_validate_json(body)
    shop = request.headers.get("x-shopify-shop-domain")
    if not shop:
        raise HTTPException(status_code=400, detail="missing_shop_header")

    svc = BillingService(shop, "", _store_for_app(request))
    if payload.topic == "app/subscription/cancelled":
        await svc.cancel_subscription()
    return {"status": "ok"}


@router.get("/status")
async def billing_status(request: Request):
    tenant = getattr(request.state, "tenant", None)
    if not tenant:
        raise HTTPException(status_code=401, detail="Missing tenant")

    store = _store_for_app(request)
    sub = await store.get_subscription(tenant.shop_domain)
    usage = await store.get_usage(tenant.shop_domain)
    plan = sub.plan_name if sub else "starter"
    plan_conf = PLANS.get(plan, {})
    trial_days_remaining = None
    if sub and sub.trial_ends_at:
        delta = sub.trial_ends_at - datetime.utcnow()
        trial_days_remaining = max(0, delta.days)

    return {
        "plan_name": plan,
        "trial_days_remaining": trial_days_remaining,
        "usage_this_month": usage.ai_calls_this_month if usage else 0,
        "usage_limit": plan_conf.get("ai_call_limit_per_month"),
        "subscription_active": (sub.status == "active") if sub else False,
    }
