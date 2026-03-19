from app.utils.logging import PIISafeFormatter


def test_logging_redacts_tokens():
    msg = "Authorization: Bearer secret-token access_token=abc123 api_key=xyz"
    redacted = PIISafeFormatter.sanitize(msg)
    assert "secret-token" not in redacted
    assert "abc123" not in redacted
    assert "xyz" not in redacted
    assert "***REDACTED***" in redacted
