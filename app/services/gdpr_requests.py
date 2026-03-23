from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)

GDPR_EVENTS_KEY = "gdpr:events"
GDPR_EVENT_TTL_SECONDS = int(os.getenv("GDPR_EVENT_TTL_SECONDS", "2592000"))  # 30 days


def _parse_payload(body: bytes) -> Dict[str, Any]:
    if not body:
        return {}
    try:
        payload = json.loads(body.decode("utf-8"))
        return payload if isinstance(payload, dict) else {"raw": payload}
    except Exception:
        return {"raw_body": body.decode("utf-8", errors="replace")}


def _customer_fields(payload: Dict[str, Any]) -> Dict[str, str]:
    customer = payload.get("customer")
    if not isinstance(customer, dict):
        customer = {}

    return {
        "customer_id": str(customer.get("id", payload.get("customer_id", "")) or ""),
        "customer_email": str(customer.get("email", payload.get("email", "")) or ""),
    }


def _record_event(redis_conn, record: Dict[str, str]) -> None:
    if not redis_conn:
        return
    try:
        redis_conn.rpush(GDPR_EVENTS_KEY, json.dumps(record, sort_keys=True))
        redis_conn.expire(GDPR_EVENTS_KEY, GDPR_EVENT_TTL_SECONDS)
    except Exception:
        logger.debug("Failed to persist GDPR event %s", record.get("event_type"), exc_info=True)


def record_data_request(
    redis_conn,
    shop_domain: str,
    body: bytes,
    request_id: str | None = None,
) -> Dict[str, str]:
    payload = _parse_payload(body)
    customer = _customer_fields(payload)
    record = {
        "event_type": "customers/data_request",
        "shop_domain": shop_domain or "",
        "customer_id": customer["customer_id"],
        "customer_email": customer["customer_email"],
        "request_id": request_id or "",
        "status": "pending_review",
        "fulfillment_mode": "manual_review",
        "customer_data_stored": "false",
        "notes": (
            "Active backend does not maintain a dedicated customer profile store. "
            "Request recorded for compliance review and merchant response handling."
        ),
        "payload_sha256": hashlib.sha256(body or b"").hexdigest(),
        "payload_json": json.dumps(payload, sort_keys=True),
        "received_at": datetime.utcnow().isoformat(),
    }
    _record_event(redis_conn, record)
    logger.info("Recorded GDPR data request for %s", shop_domain or "unknown")
    return record


def record_customer_redaction(
    redis_conn,
    shop_domain: str,
    body: bytes,
    request_id: str | None = None,
) -> Dict[str, str]:
    payload = _parse_payload(body)
    customer = _customer_fields(payload)
    record = {
        "event_type": "customers/redact",
        "shop_domain": shop_domain or "",
        "customer_id": customer["customer_id"],
        "customer_email": customer["customer_email"],
        "request_id": request_id or "",
        "status": "completed_no_customer_records",
        "fulfillment_mode": "no_customer_store_detected",
        "customer_data_stored": "false",
        "notes": (
            "Request recorded. The active backend does not persist dedicated customer "
            "records, so no shop-level uninstall cleanup was triggered."
        ),
        "payload_sha256": hashlib.sha256(body or b"").hexdigest(),
        "payload_json": json.dumps(payload, sort_keys=True),
        "received_at": datetime.utcnow().isoformat(),
    }
    _record_event(redis_conn, record)
    logger.info("Recorded GDPR customer redaction for %s", shop_domain or "unknown")
    return record
