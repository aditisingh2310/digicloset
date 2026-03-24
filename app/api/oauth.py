from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import logging
import time
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, HTTPException, Request, Depends, Response, Cookie
from starlette.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.db.models import SessionLocal, Shop

from app.core.config import settings
from app.core.security import verify_oauth_hmac
from app.services.shopify_client import ShopifyClient

router = APIRouter(prefix="/auth", tags=["auth"])
SHOP_DOMAIN_RE = re.compile(r"^[a-z0-9][a-z0-9-]*\.myshopify\.com$")
logger = logging.getLogger(__name__)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _redis(request: Request) -> Optional[object]:
    return getattr(request.app.state, "redis", None)


def _is_secure_request(request: Request) -> bool:
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    return proto == "https"


def _make_oauth_state(shop: str) -> str:
    payload = {
        "shop": shop,
        "nonce": secrets.token_urlsafe(8),
        "iat": int(time.time()),
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    ).decode().rstrip("=")
    signature = hmac.new(
        settings.shopify_api_secret.encode(), encoded.encode(), hashlib.sha256
    ).hexdigest()
    return f"{encoded}.{signature}"


def _decode_oauth_state(state: str, shop: str, max_age_seconds: int = 300) -> None:
    try:
        encoded, signature = state.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid OAuth state") from exc

    expected_signature = hmac.new(
        settings.shopify_api_secret.encode(), encoded.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected_signature, signature):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    padding = "=" * (-len(encoded) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(encoded + padding).decode())
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid OAuth state") from exc

    if payload.get("shop") != shop:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    issued_at = int(payload.get("iat", 0))
    if issued_at <= 0 or (time.time() - issued_at) > max_age_seconds:
        raise HTTPException(status_code=400, detail="OAuth state expired")


def _redis_get(redis_client: Optional[object], key: str) -> Optional[str]:
    if not redis_client:
        return None
    try:
        return redis_client.get(key)
    except Exception as exc:
        logger.warning("Redis read failed during OAuth flow: %s", exc)
        return None


def _redis_setex(redis_client: Optional[object], key: str, ttl: int, value: str) -> bool:
    if not redis_client:
        return False
    try:
        redis_client.setex(key, ttl, value)
        return True
    except Exception as exc:
        logger.warning("Redis write failed during OAuth flow: %s", exc)
        return False


def _redis_delete(redis_client: Optional[object], key: str) -> None:
    if not redis_client:
        return None
    try:
        redis_client.delete(key)
    except Exception as exc:
        logger.warning("Redis delete failed during OAuth flow: %s", exc)


def _validate_shop_domain(shop: str) -> str:
    shop = (shop or "").strip().lower()
    if not SHOP_DOMAIN_RE.match(shop):
        raise HTTPException(status_code=400, detail="Invalid shop domain")
    return shop


@router.get("/install")
async def shopify_install(request: Request, shop: str):
    shop = _validate_shop_domain(shop)
    state = _make_oauth_state(shop)
    redis_client = _redis(request)
    _redis_setex(redis_client, f"oauth_state:{state}", 300, shop)

    app_base = request.headers.get("x-forwarded-proto", request.url.scheme) + "://" + request.headers.get("host", request.url.netloc)
    params = {
        "client_id": settings.shopify_api_key,
        "scope": "read_products,write_products,read_customers,write_content",
        "redirect_uri": f"{app_base}/api/auth/callback",
        "state": state,
    }
    install_url = f"https://{shop}/admin/oauth/authorize?{urlencode(params)}"
    response = JSONResponse({"install_url": install_url, "state": state})
    response.set_cookie(
        "oauth_state",
        state,
        httponly=True,
        secure=_is_secure_request(request),
        samesite="lax",
        max_age=300,
    )
    return response


@router.get("/callback")
async def shopify_callback(
    request: Request,
    response: Response,
    state: Optional[str] = None,
    session_id: Optional[str] = Cookie(None),
    oauth_state: Optional[str] = Cookie(None),
    db: Session = Depends(get_db),
):
    # Verify HMAC and state parameter
    qs = dict(request.query_params)
    verify_oauth_hmac(qs)

    shop = _validate_shop_domain(qs.get("shop", ""))
    code = qs.get("code")
    returned_state = qs.get("state")
    if not code or not returned_state:
        raise HTTPException(status_code=400, detail="Missing code/state")

    _decode_oauth_state(returned_state, shop)
    redis_client = _redis(request)
    stored_shop = _redis_get(redis_client, f"oauth_state:{returned_state}")
    if stored_shop is not None:
        if stored_shop != shop:
            raise HTTPException(status_code=400, detail="Invalid OAuth state")
        _redis_delete(redis_client, f"oauth_state:{returned_state}")
    elif oauth_state != returned_state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

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
    access_token = token_res.json().get("access_token")
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
    app_base_url = request.headers.get("x-forwarded-proto", request.url.scheme) + "://" + request.headers.get("host", request.url.netloc)
    callback_base = settings.app_url.rstrip("/") if settings.app_url else app_base_url
    client = ShopifyClient(shop, access_token)
    webhooks = [
        {"topic": "app/uninstalled", "address": f"{callback_base}/api/webhooks/app-uninstalled"},
        {"topic": "customers/data_request", "address": f"{callback_base}/api/webhooks/customers/data_request"},
        {"topic": "customers/redact", "address": f"{callback_base}/api/webhooks/customers/redact"},
        {"topic": "shop/redact", "address": f"{callback_base}/api/webhooks/shop/redact"},
    ]
    for webhook in webhooks:
        try:
            client.request("POST", "/admin/api/2024-01/webhooks.json", json={"webhook": webhook})
        except Exception as e:
            logger.warning("Failed to register webhook %s: %s", webhook["topic"], e)

    # Store token server-side in Redis with a session id and set secure cookie
    sess = secrets.token_urlsafe(32)
    if redis_client:
        try:
            redis_client.setex(f"session:{sess}", 3600 * 24 * 7, json.dumps({"shop": shop, "access_token": access_token}))
            redis_client.setex(f"session_shop:{sess}", 3600 * 24 * 7, shop)
            redis_client.sadd(f"shop_sessions:{shop}", sess)
            redis_client.expire(f"shop_sessions:{shop}", 3600 * 24 * 30)
        except Exception as exc:
            logger.warning("Redis session persistence failed during OAuth callback: %s", exc)

    response = RedirectResponse(url="/")
    response.delete_cookie("oauth_state")
    response.set_cookie(
        "session_id",
        sess,
        httponly=True,
        secure=_is_secure_request(request),
        samesite="lax",
        max_age=3600 * 24 * 7,
    )
    return response
