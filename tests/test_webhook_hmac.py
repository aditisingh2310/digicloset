def test_invalid_webhook_hmac(client):
    res = client.post("/api/webhooks/app-uninstalled", data=b"{}", headers={"X-Shopify-Hmac-Sha256": "bad"})
    assert res.status_code == 400
    body = res.json()
    assert body.get("error") == "Invalid webhook signature"
    assert body.get("status") == 400
    assert body.get("request_id")
