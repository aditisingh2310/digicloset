def test_validation_error_schema(client, tenant_headers_a):
    # Missing required field triggers validation error
    res = client.post("/api/merchant/settings", json={}, headers=tenant_headers_a)
    assert res.status_code == 422
    payload = res.json()
    assert payload.get("code") == "VALIDATION_ERROR"
    assert payload.get("request_id")
    assert payload.get("status") == 422
