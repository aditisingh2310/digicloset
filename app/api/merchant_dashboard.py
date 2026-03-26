"""Merchant dashboard endpoints for launch-ready embedded admin views."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/merchant", tags=["merchant-dashboard"])


class WidgetSettingsUpdate(BaseModel):
    widget_enabled: bool = Field(..., description="Enable storefront try-on widget")


@router.get("/dashboard")
async def dashboard_summary(request: Request) -> Dict[str, Any]:
    """Return minimal dashboard counters required by merchant admin UI."""
    tenant = getattr(request.state, "tenant", None)
    shop = getattr(tenant, "shop_domain", None) or request.headers.get("x-shopify-shop-domain", "unknown")
    redis_client = getattr(request.app.state, "redis", None)
    dev_state = getattr(request.app.state, "dev_merchant_state", {})

    if not redis_client:
        local_state = dev_state.get(shop, {})
        return {
            "shop": shop,
            "tryons_generated": local_state.get("tryons_generated", 0),
            "credits_used": local_state.get("credits_used", 0),
            "generation_history": local_state.get("generation_history", []),
            "widget_enabled": local_state.get("widget_enabled", True),
        }

    try:
        tryons = int(redis_client.get(f"merchant:{shop}:tryons_generated") or 0)
        credits = int(redis_client.get(f"merchant:{shop}:credits_used") or 0)
        history_raw: List[str] = redis_client.lrange(f"merchant:{shop}:generation_history", 0, 49) or []
        history = []
        for row in history_raw:
            try:
                history.append(__import__("json").loads(row))
            except Exception:
                continue
        widget_enabled = (redis_client.get(f"merchant:{shop}:widget_enabled") or "false").lower() == "true"

        return {
            "shop": shop,
            "tryons_generated": tryons,
            "credits_used": credits,
            "generation_history": history,
            "widget_enabled": widget_enabled,
        }
    except Exception:
        local_state = dev_state.get(shop, {})
        return {
            "shop": shop,
            "tryons_generated": local_state.get("tryons_generated", 0),
            "credits_used": local_state.get("credits_used", 0),
            "generation_history": local_state.get("generation_history", []),
            "widget_enabled": local_state.get("widget_enabled", True),
        }


@router.post("/settings")
async def update_settings(payload: WidgetSettingsUpdate, request: Request) -> Dict[str, Any]:
    """Toggle storefront widget state used by theme app extension."""
    tenant = getattr(request.state, "tenant", None)
    shop = getattr(tenant, "shop_domain", None) or request.headers.get("x-shopify-shop-domain", "unknown")
    redis_client = getattr(request.app.state, "redis", None)
    dev_state = getattr(request.app.state, "dev_merchant_state", None)
    if redis_client:
        try:
            redis_client.set(f"merchant:{shop}:widget_enabled", "true" if payload.widget_enabled else "false")
        except Exception:
            redis_client = None
    if dev_state is not None and not redis_client:
        current = dev_state.setdefault(shop, {})
        current["widget_enabled"] = payload.widget_enabled
    return {"shop": shop, "widget_enabled": payload.widget_enabled, "updated_at": datetime.utcnow().isoformat()}
