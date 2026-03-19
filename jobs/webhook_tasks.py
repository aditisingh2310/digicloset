from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any

from jobs.redis_conn import get_redis_connection
from app.services.data_deletion import DataDeletionService
from app.db.models import SessionLocal

logger = logging.getLogger(__name__)

WEBHOOK_STATUS_TTL_SECONDS = 60 * 60 * 24 * 2  # 2 days
WEBHOOK_DLQ_KEY = "webhook:dead_letter"


def _status_key(delivery_key: str) -> str:
    return f"webhook:delivery:{delivery_key}"


def _update_status(redis_conn, delivery_key: str, **fields: Any) -> None:
    if not redis_conn:
        return
    try:
        redis_conn.hset(_status_key(delivery_key), mapping=fields)
        redis_conn.expire(_status_key(delivery_key), WEBHOOK_STATUS_TTL_SECONDS)
    except Exception:
        logger.debug("Failed to update webhook status for %s", delivery_key, exc_info=True)


def _increment_attempts(redis_conn, delivery_key: str) -> None:
    if not redis_conn:
        return
    try:
        redis_conn.hincrby(_status_key(delivery_key), "attempts", 1)
    except Exception:
        logger.debug("Failed to increment webhook attempts for %s", delivery_key, exc_info=True)


def _already_completed(redis_conn, delivery_key: str) -> bool:
    if not redis_conn:
        return False
    try:
        status = redis_conn.hget(_status_key(delivery_key), "status")
        return status == "completed"
    except Exception:
        return False


def _record_dead_letter(redis_conn, payload: Dict[str, Any]) -> None:
    if not redis_conn:
        return
    try:
        redis_conn.rpush(WEBHOOK_DLQ_KEY, json.dumps(payload))
        redis_conn.expire(WEBHOOK_DLQ_KEY, WEBHOOK_STATUS_TTL_SECONDS)
    except Exception:
        logger.debug("Failed to push webhook DLQ record", exc_info=True)


def _run_uninstall_cleanup(shop_domain: str, redis_conn) -> Dict[str, Any]:
    """Execute hard-delete cleanup for a shop."""
    if not shop_domain:
        raise ValueError("missing_shop_domain")

    db = SessionLocal()
    try:
        deletion = DataDeletionService(db=db, redis=redis_conn)
        audit = asyncio.run(deletion.delete_shop_data(shop_domain))
        return audit.model_dump() if hasattr(audit, "model_dump") else audit.dict()
    finally:
        db.close()


def process_webhook(
    delivery_key: str,
    topic: str,
    shop_domain: str,
    body: bytes,
    headers: Dict[str, str],
    request_id: str | None = None,
) -> Dict[str, Any]:
    """RQ worker entry point for processing Shopify webhooks."""
    redis_conn = get_redis_connection(decode_responses=True)

    if _already_completed(redis_conn, delivery_key):
        return {"status": "duplicate"}

    _increment_attempts(redis_conn, delivery_key)
    _update_status(
        redis_conn,
        delivery_key,
        status="processing",
        last_attempt_at=datetime.utcnow().isoformat(),
    )

    try:
        if topic in {"app/uninstalled", "customers/redact", "shop/redact"}:
            audit = _run_uninstall_cleanup(shop_domain, redis_conn)
            _update_status(
                redis_conn,
                delivery_key,
                status="completed",
                completed_at=datetime.utcnow().isoformat(),
            )
            return {"status": "completed", "audit": audit}

        if topic in {"customers/data_request"}:
            logger.info("Received GDPR data_request for %s", shop_domain)
            _update_status(
                redis_conn,
                delivery_key,
                status="completed",
                completed_at=datetime.utcnow().isoformat(),
            )
            return {"status": "completed"}

        # Unknown or unhandled webhook topic
        logger.warning("Unhandled webhook topic: %s", topic)
        _update_status(
            redis_conn,
            delivery_key,
            status="completed",
            completed_at=datetime.utcnow().isoformat(),
        )
        return {"status": "completed", "note": "unhandled topic"}

    except Exception as exc:
        _update_status(
            redis_conn,
            delivery_key,
            status="failed",
            last_error=str(exc),
            failed_at=datetime.utcnow().isoformat(),
        )

        try:
            from rq import get_current_job
        except Exception:
            get_current_job = None

        retries_left = 0
        if get_current_job:
            job = get_current_job()
            if job and job.retries_left is not None:
                retries_left = int(job.retries_left)

        if retries_left <= 0:
            _record_dead_letter(
                redis_conn,
                {
                    "delivery_key": delivery_key,
                    "topic": topic,
                    "shop_domain": shop_domain,
                    "error": str(exc),
                    "request_id": request_id or "",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        raise
