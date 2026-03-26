import time
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.models.billing import SubscriptionRecord


USER_IMAGE = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'><rect width='40' height='40' fill='%23dbeafe'/><circle cx='20' cy='14' r='7' fill='%2394a3b8'/><rect x='11' y='22' width='18' height='12' rx='6' fill='%2364748b'/></svg>"
GARMENT_IMAGE = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'><rect width='40' height='40' fill='%23f8fafc'/><path d='M10 10h20l-4 8v12H14V18z' fill='%231f6b53'/></svg>"


def test_tryon_generation_flow_updates_dashboard(client, tenant_headers_a):
    response = client.post(
        "/api/v1/try-on/generate",
        json={
            "user_image_url": USER_IMAGE,
            "garment_image_url": GARMENT_IMAGE,
            "product_id": "demo-hoodie",
        },
        headers=tenant_headers_a,
    )

    assert response.status_code == 200
    payload = response.json()
    job_id = payload["job_id"]

    completed = None
    for _ in range(10):
        status_response = client.get(f"/api/v1/try-on/{job_id}", headers=tenant_headers_a)
        assert status_response.status_code == 200
        status_payload = status_response.json()
        if status_payload["status"] == "completed":
            completed = status_payload
            break
        time.sleep(0.25)

    assert completed is not None
    assert completed["image_url"] == f"/api/v1/try-on/{job_id}/image"

    image_response = client.get(completed["image_url"], headers=tenant_headers_a)
    assert image_response.status_code == 200
    assert image_response.headers["content-type"].startswith("image/svg+xml")
    assert "Virtual try-on result" in image_response.text

    dashboard_response = client.get("/api/merchant/dashboard", headers=tenant_headers_a)
    assert dashboard_response.status_code == 200
    dashboard_payload = dashboard_response.json()
    assert dashboard_payload["tryons_generated"] >= 1
    assert dashboard_payload["generation_history"][0]["product_id"] == "demo-hoodie"


def test_localhost_dev_tenant_can_access_admin_without_headers(inject_redis, monkeypatch):
    monkeypatch.setattr(settings, "debug", True, raising=False)
    app.state.store.subs[settings.dev_shop_domain] = SubscriptionRecord(
        shop_domain=settings.dev_shop_domain,
        status="active",
        plan_name="starter",
        trial_ends_at=datetime.utcnow() + timedelta(days=7),
        activated_at=datetime.utcnow(),
    )

    client = TestClient(app, base_url="http://localhost")

    response = client.get("/api/merchant/dashboard")

    assert response.status_code == 200
    assert response.json()["shop"] == settings.dev_shop_domain
