import os
import requests
import pytest
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv('VITE_API_BASE_URL') or os.getenv('API_BASE_URL') or 'http://localhost:8000'

def _server_available() -> bool:
    for path in ("/health", "/"):
        try:
            r = requests.get(f"{API_BASE}{path}", timeout=2)
            if r.status_code < 500:
                return True
        except requests.RequestException:
            continue
    return False


@pytest.mark.skipif(not _server_available(), reason="Integration API not running")
def test_health():
    # Prefer /health when available; fallback to root for legacy services.
    try:
        r = requests.get(f"{API_BASE}/health", timeout=5)
        if r.status_code == 404:
            r = requests.get(f"{API_BASE}/", timeout=5)
    except requests.RequestException as exc:
        pytest.skip(f"API unavailable: {exc}")
    assert r.status_code == 200


@pytest.mark.skipif(not _server_available(), reason="Integration API not running")
def test_public_app_routes():
    privacy = requests.get(f"{API_BASE}/privacy", timeout=5)
    assert privacy.status_code == 200
    assert "Replace with your real policy" not in privacy.text

    terms = requests.get(f"{API_BASE}/terms", timeout=5)
    assert terms.status_code == 200
    assert "Replace with your real terms" not in terms.text

    install = requests.get(
        f"{API_BASE}/api/auth/install",
        params={"shop": "integration-check.myshopify.com"},
        timeout=5,
    )
    assert install.status_code == 200
    payload = install.json()
    assert payload.get("state")
    assert "integration-check.myshopify.com" in payload.get("install_url", "")
    assert "/admin/oauth/authorize" in payload.get("install_url", "")

if __name__ == "__main__":
    try:
        print(f"Running tests against {API_BASE}...")
        
        test_health()
        print("Health check passed!")
        
        try:
            from pathlib import Path
            test_public_app_routes()
            print("Public route flow passed!")
        except Exception as e:
            print(f"Try-on flow failed: {e}")
            raise e

        print("All tests passed!")
    except Exception as e:
        print(f"CRITICAL FAILURE: {e}")
        exit(1)
