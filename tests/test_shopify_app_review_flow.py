import base64
import hashlib
import hmac
import time

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.models import SessionLocal, Shop
from app.api.webhooks import make_idempotency_key_for_webhook
from jobs.webhook_tasks import process_webhook


def shopify_hmac(body: bytes) -> str:
    """Compute correct Shopify webhook HMAC (base64 + sha256)."""
    return base64.b64encode(
        hmac.new(settings.shopify_api_secret.encode(), body, hashlib.sha256).digest()
    ).decode()


def oauth_hmac(params: dict) -> str:
    """Compute Shopify OAuth query HMAC (query param style)."""
    sorted_items = sorted((k, v) for k, v in params.items() if k != "hmac")
    message = "&".join(f"{k}={v}" for k, v in sorted_items)
    return hmac.new(settings.shopify_api_secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def test_health_endpoint(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json().get("status") == "ok"


@pytest.mark.parametrize("endpoint", [
    "/api/webhooks/customers/data_request",
    "/api/webhooks/customers/redact",
    "/api/webhooks/shop/redact",
    "/api/webhooks/app-uninstalled",
])
def test_all_webhook_hmac_valid_invalid(client: TestClient, endpoint: str):
    body = b"{\"request\": \"data\"}"
    good_sig = shopify_hmac(body)

    # valid signature should be accepted
    r = client.post(endpoint, content=body, headers={
        "X-Shopify-Hmac-Sha256": good_sig,
        "X-Shopify-Shop-Domain": "testshop.myshopify.com",
    })
    assert r.status_code == 200
    assert r.json().get("status") in ("accepted", "duplicate", "completed")

    # invalid signature should be rejected
    r = client.post(endpoint, content=body, headers={
        "X-Shopify-Hmac-Sha256": "invalidsig",
        "X-Shopify-Shop-Domain": "testshop.myshopify.com",
    })
    assert r.status_code == 401


def test_webhook_handlers_do_not_block(client: TestClient):
    body = b"{}"
    headers = {
        "X-Shopify-Hmac-Sha256": shopify_hmac(body),
        "X-Shopify-Shop-Domain": "testing.myshopify.com",
    }

    start = time.monotonic()
    response = client.post("/api/webhooks/app-uninstalled", content=body, headers=headers)
    elapsed = time.monotonic() - start

    assert response.status_code == 200
    assert elapsed < 5


def test_uninstall_flow_end_to_end_is_idempotent(client: TestClient, monkeypatch):
    # set up shop record as installed
    db = SessionLocal()
    shop_domain = "uninstall-rookie.myshopify.com"
    existing = db.query(Shop).filter(Shop.domain == shop_domain).first()
    if existing:
        db.delete(existing)
        db.commit()

    db_shop = Shop(domain=shop_domain, access_token="token123")
    db.add(db_shop)
    db.commit()

    # Step 1: hit app/uninstalled webhook with real HMAC
    body = b"{}"
    headers = {
        "X-Shopify-Hmac-Sha256": shopify_hmac(body),
        "X-Shopify-Shop-Domain": shop_domain,
    }

    # Ensure app responds safely to webhook call
    res1 = client.post("/api/webhooks/app-uninstalled", content=body, headers=headers)
    assert res1.status_code == 200
    assert res1.json().get("status") in ("completed", "accepted", "duplicate")

    # Simulate worker processing logic (must be safe to call from outside webhook)
    from app.services.data_deletion import DataDeletionService

    asyncio_result = __import__("asyncio")
    asyncio_result.run(DataDeletionService(db=db, redis=client.app.state.redis).delete_shop_data(shop_domain))

    db.refresh(db_shop)
    assert db_shop.access_token in ("", None)

    # Idempotent: second deletion does not fail or drop data unexpectedly
    asyncio_result.run(DataDeletionService(db=db, redis=client.app.state.redis).delete_shop_data(shop_domain))
    db.refresh(db_shop)
    assert db_shop.access_token in ("", None)

    # Call webhook again, still 200 stable.
    res2 = client.post("/api/webhooks/app-uninstalled", content=body, headers=headers)
    assert res2.status_code == 200
    assert res2.json().get("status") in ("completed", "accepted", "duplicate")

    db.close()


def test_oauth_flow_rejection_and_replay(client: TestClient, monkeypatch):
    # get install state
    install_resp = client.get("/api/auth/install", params={"shop": "replay-test.myshopify.com"})
    assert install_resp.status_code == 200
    state = install_resp.json()["state"]

    # missing state should fail
    bad_state_resp = client.get("/api/auth/callback", params={"shop": "replay-test.myshopify.com", "code": "abc", "hmac": "bad"})
    assert bad_state_resp.status_code in (400, 401)

    # wrong state should fail
    wrong_state_req = {
        "shop": "replay-test.myshopify.com",
        "code": "abc",
        "state": "wrong-st",
    }
    wrong_state_req["hmac"] = oauth_hmac(wrong_state_req)
    wrong_state_resp = client.get("/api/auth/callback", params=wrong_state_req)
    assert wrong_state_resp.status_code in (400, 401)

    # valid callback with mocked token exchange
    class FakeShopifyClient:
        def __init__(self, shop_domain, access_token):
            self.shop_domain = shop_domain
            self.access_token = access_token

        def request(self, method, path, json=None, params=None, timeout=None, idempotency_key=None):
            class FakeResp:
                status_code = 201
                ok = True
                headers = {}
                def raise_for_status(self):
                    return None
                def json(self):
                    return {}

            return FakeResp()

    monkeypatch.setattr("app.api.oauth.ShopifyClient", FakeShopifyClient)

    def fake_requests_post(url, json, timeout):
        class FakeResp:
            status_code = 200
            ok = True
            def raise_for_status(self):
                return None
            def json(self):
                return {"access_token": "token-xyz"}

        return FakeResp()

    monkeypatch.setattr("requests.post", fake_requests_post)

    valid_req = {
        "shop": "replay-test.myshopify.com",
        "code": "abc",
        "state": state,
    }
    valid_req["hmac"] = oauth_hmac(valid_req)

    good_resp = client.get("/api/auth/callback", params=valid_req, follow_redirects=False)
    assert good_resp.status_code in (302, 307)

    # replay same callback should fail because state gets consumed
    replay_req = valid_req.copy()
    replay_req["hmac"] = oauth_hmac(replay_req)  # recompute for same params
    replay_resp = client.get("/api/auth/callback", params=replay_req)
    assert replay_resp.status_code in (400, 401)

    # validate token persisted once
    db = SessionLocal()
    shop = db.query(Shop).filter(Shop.domain == "replay-test.myshopify.com").first()
    assert shop is not None
    assert shop.access_token == "token-xyz"
    db.close()


def test_oauth_hmac_tampering_rejected(client: TestClient):
    params = {
        "shop": "tamper-test.myshopify.com",
        "code": "abc",
        "state": "one",
        "hmac": "wrong",
    }
    response = client.get("/api/auth/callback", params=params)
    assert response.status_code == 401


def test_oauth_consistency_no_token_on_invalid_install(client: TestClient):
    params = {"shop": "invalid-install.myshopify.com", "code": "abc", "state": "s1", "hmac": "bad"}
    client.get("/api/auth/callback", params=params)
    db = SessionLocal()
    shop = db.query(Shop).filter(Shop.domain == "invalid-install.myshopify.com").first()
    assert shop is None
    db.close()
