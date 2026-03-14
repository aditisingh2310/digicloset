from __future__ import annotations

import json
import secrets
from datetime import datetime
from typing import Optional

import requests
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from starlette.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.db.models import SessionLocal, Shop

from app.core.config import settings
from app.core.security import verify_oauth_hmac
from app.services.shopify_client import ShopifyClient

router = APIRouter(prefix="/auth", tags=["auth"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _redis() -> Optional[object]:
    # lazily import app state redis; caller must ensure running inside FastAPI app context
    from fastapi import _get_current_app

    app = _get_current_app()
    return getattr(app.state, "redis", None)


@router.get("/install")
async def shopify_install(shop: str):
    state = secrets.token_urlsafe(16)
    r = _redis()
    if r:
        # store state -> shop mapping short-lived (5 minutes)
        r.setex(f"oauth_state:{state}", 300, shop)

    params = {
        "client_id": settings.shopify_api_key,
        "scope": "read_products,write_products,read_customers,write_content",
        "redirect_uri": f"/api/auth/callback",
        "state": state,
    }
    install_url = f"https://{shop}/admin/oauth/authorize?" + "&".join(f"{k}={v}" for k, v in params.items())
    return {"install_url": install_url, "state": state}


@router.get("/callback")
async def shopify_callback(request: Request, response: Response, state: Optional[str] = None, session_id: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    # Verify HMAC and state parameter
    qs = dict(request.query_params)
    verify_oauth_hmac(qs)

    shop = qs.get("shop")
    code = qs.get("code")
    returned_state = qs.get("state")
    if not shop or not code:
        raise HTTPException(status_code=400, detail="Missing shop or code")

    if returned_state != state:
        # also check server-side stored state mapping
        r = _redis()
        if not r or not r.get(f"oauth_state:{returned_state}"):
            raise HTTPException(status_code=400, detail="Invalid state")

    # Exchange code for access token
    token_res = requests.post(
        f"https://{shop}/admin/oauth/access_token",
        json={
            "client_id": settings.shopify_api_key,
            "client_secret": settings.shopify_api_secret,
            "code": code,
        },
        timeout=10,
    )
    token_res.raise_for_status()
    body = token_res.json()
    access_token = body.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Failed to obtain access token")

    # Store in DB
    existing_shop = db.query(Shop).filter(Shop.domain == shop).first()
    if existing_shop:
        existing_shop.access_token = access_token
        existing_shop.installed_at = datetime.utcnow()
    else:
        new_shop = Shop(domain=shop, access_token=access_token)
        db.add(new_shop)
    db.commit()

    # Register webhooks
    client = ShopifyClient(shop, access_token)
    webhooks = [
        {"topic": "app/uninstalled", "address": f"{settings.base_url}/api/webhooks/app_uninstalled"},
        {"topic": "shop/update", "address": f"{settings.base_url}/api/webhooks/shop_update"},
        {"topic": "customers/data_request", "address": f"{settings.base_url}/api/webhooks/customers_data_request"},
        {"topic": "customers/redact", "address": f"{settings.base_url}/api/webhooks/customers_redact"},
        {"topic": "shop/redact", "address": f"{settings.base_url}/api/webhooks/shop_redact"},
    ]
    for webhook in webhooks:
        try:
            client.request("POST", "/admin/api/2024-01/webhooks.json", json={"webhook": webhook})
        except Exception as e:
            print(f"Failed to register webhook {webhook['topic']}: {e}")

    # Store token server-side in Redis with a session id and set secure cookie
    sess = secrets.token_urlsafe(32)
    r = _redis()
    if r:
        r.setex(f"session:{sess}", 3600 * 24 * 7, json.dumps({"shop": shop, "access_token": access_token}))

    # set cookie with HttpOnly, Secure and SameSite=Lax to reduce CSRF
    response = RedirectResponse(url="/" )
    response.set_cookie("session_id", sess, httponly=True, secure=True, samesite="lax", max_age=3600 * 24 * 7)

    return response
