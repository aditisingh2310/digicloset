import hashlib
import hmac

from app.core.config import settings
from app.main import app


def _oauth_hmac(params: dict) -> str:
    sorted_items = sorted((k, v) for k, v in params.items() if k != "hmac")
    message = "&".join(f"{k}={v}" for k, v in sorted_items)
    return hmac.new(settings.shopify_api_secret.encode(), message.encode(), hashlib.sha256).hexdigest()


class FailingRedis:
    def setex(self, *args, **kwargs):
        raise ConnectionError("redis unavailable")

    def get(self, *args, **kwargs):
        raise ConnectionError("redis unavailable")

    def delete(self, *args, **kwargs):
        raise ConnectionError("redis unavailable")

    def sadd(self, *args, **kwargs):
        raise ConnectionError("redis unavailable")

    def expire(self, *args, **kwargs):
        raise ConnectionError("redis unavailable")


def test_install_succeeds_when_redis_is_unavailable(client):
    app.state.redis = FailingRedis()

    response = client.get("/api/auth/install", params={"shop": "fallback-state.myshopify.com"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["install_url"].startswith("https://fallback-state.myshopify.com/admin/oauth/authorize?")
    assert payload["state"]
    assert response.cookies.get("oauth_state") == payload["state"]


def test_callback_uses_cookie_state_fallback_when_redis_is_unavailable(client, monkeypatch):
    app.state.redis = FailingRedis()
    shop = "fallback-state.myshopify.com"

    install_response = client.get("/api/auth/install", params={"shop": shop})
    state = install_response.json()["state"]

    class FakeShopifyClient:
        def __init__(self, shop_domain, access_token):
            self.shop_domain = shop_domain
            self.access_token = access_token

        def request(self, method, path, json=None, params=None, timeout=None, idempotency_key=None):
            class FakeResponse:
                status_code = 201
                ok = True
                headers = {}

                def raise_for_status(self):
                    return None

                def json(self):
                    return {}

            return FakeResponse()

    def fake_requests_post(url, json, timeout):
        class FakeTokenResponse:
            status_code = 200
            ok = True

            def raise_for_status(self):
                return None

            def json(self):
                return {"access_token": "oauth-token"}

        return FakeTokenResponse()

    monkeypatch.setattr("app.api.oauth.ShopifyClient", FakeShopifyClient)
    monkeypatch.setattr("requests.post", fake_requests_post)

    params = {
        "shop": shop,
        "code": "auth-code",
        "state": state,
    }
    params["hmac"] = _oauth_hmac(params)

    callback_response = client.get("/api/auth/callback", params=params, follow_redirects=False)

    assert callback_response.status_code in (302, 307)
    assert callback_response.headers["location"] == "/"


def test_callback_rejects_cookie_mismatch_when_redis_is_unavailable(client, monkeypatch):
    app.state.redis = FailingRedis()
    shop = "fallback-state.myshopify.com"

    install_response = client.get("/api/auth/install", params={"shop": shop})
    state = install_response.json()["state"]
    client.cookies.set("oauth_state", "different-state")

    params = {
        "shop": shop,
        "code": "auth-code",
        "state": state,
    }
    params["hmac"] = _oauth_hmac(params)

    response = client.get("/api/auth/callback", params=params, follow_redirects=False)

    assert response.status_code == 400
    assert "Invalid OAuth state" in response.text
