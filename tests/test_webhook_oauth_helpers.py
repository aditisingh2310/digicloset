import base64
import hashlib
import hmac
from fastapi.testclient import TestClient

from app.core.config import settings


def shopify_hmac(headers_or_body: bytes) -> str:
    """Compute Shopify webhook signature for testing."""
    return base64.b64encode(hmac.new(settings.shopify_api_secret.encode(), headers_or_body, hashlib.sha256).digest()).decode()


def post_shopify_webhook(client: TestClient, path: str, body: bytes, shop: str = "test-shop.myshopify.com"):
    """Send a signed webhook request to the app."""
    signature = shopify_hmac(body)
    return client.post(
        path,
        content=body,
        headers={
            "X-Shopify-Hmac-Sha256": signature,
            "X-Shopify-Shop-Domain": shop,
            "X-Shopify-Topic": path.split("/")[-1].replace("-","/"),
        },
    )


def callback_oauth(client: TestClient, shop: str, code: str, state: str):
    """Simulate OAuth callback request with correct Shopify oauth HMAC."""
    params = {
        "shop": shop,
        "code": code,
        "state": state,
    }
    message = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    signature = hmac.new(
        settings.shopify_api_secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()
    params["hmac"] = signature

    return client.get("/api/auth/callback", params=params)
