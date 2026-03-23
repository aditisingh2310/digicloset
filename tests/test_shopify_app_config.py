import tomllib
from pathlib import Path


def test_shopify_app_config_includes_required_compliance_webhooks():
    config_path = Path(__file__).resolve().parents[1] / "shopify.app.toml"
    assert config_path.exists(), "shopify.app.toml should exist at the repo root"

    config = tomllib.loads(config_path.read_text(encoding="utf-8"))

    assert config["embedded"] is True
    assert "/api/auth/callback" in config["auth"]["redirect_urls"][0]

    subscriptions = config["webhooks"]["subscriptions"]
    assert len(subscriptions) == 4

    topic_map = {}
    for subscription in subscriptions:
        if "topics" in subscription:
            topic_map[tuple(subscription["topics"])] = subscription["uri"]
        if "compliance_topics" in subscription:
            topic_map[tuple(subscription["compliance_topics"])] = subscription["uri"]

    assert topic_map[("app/uninstalled",)] == "/api/webhooks/app-uninstalled"
    assert topic_map[("customers/data_request",)] == "/api/webhooks/customers/data_request"
    assert topic_map[("customers/redact",)] == "/api/webhooks/customers/redact"
    assert topic_map[("shop/redact",)] == "/api/webhooks/shop/redact"
