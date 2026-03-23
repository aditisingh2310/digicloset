import hashlib
import hmac

from app.core.config import settings


def _oauth_hmac(params: dict) -> str:
    sorted_items = sorted((k, v) for k, v in params.items() if k != "hmac")
    message = "&".join(f"{k}={v}" for k, v in sorted_items)
    return hmac.new(settings.shopify_api_secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def test_oauth_callback_registers_all_required_compliance_webhooks(client, monkeypatch):
    install_response = client.get("/api/auth/install", params={"shop": "register-hooks.myshopify.com"})
    assert install_response.status_code == 200
    state = install_response.json()["state"]

    registrations = []

    class FakeShopifyClient:
        def __init__(self, shop_domain, access_token):
            self.shop_domain = shop_domain
            self.access_token = access_token

        def request(self, method, path, json=None, params=None, timeout=None, idempotency_key=None):
            registrations.append({"method": method, "path": path, "json": json})

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
        "shop": "register-hooks.myshopify.com",
        "code": "auth-code",
        "state": state,
    }
    params["hmac"] = _oauth_hmac(params)

    callback_response = client.get("/api/auth/callback", params=params, follow_redirects=False)

    assert callback_response.status_code in (302, 307)
    assert len(registrations) == 4

    topics = [item["json"]["webhook"]["topic"] for item in registrations]
    addresses = [item["json"]["webhook"]["address"] for item in registrations]

    assert topics == [
        "app/uninstalled",
        "customers/data_request",
        "customers/redact",
        "shop/redact",
    ]
    assert all(address.endswith(path) for address, path in zip(
        addresses,
        [
            "/api/webhooks/app-uninstalled",
            "/api/webhooks/customers/data_request",
            "/api/webhooks/customers/redact",
            "/api/webhooks/shop/redact",
        ],
    ))
