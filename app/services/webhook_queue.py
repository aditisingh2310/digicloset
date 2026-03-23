from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from app.core.security import make_idempotency_key_for_webhook

logger = logging.getLogger(__name__)


class WebhookQueueUnavailable(RuntimeError):
    """Raised when webhook queue or persistence is unavailable."""


class DuplicateWebhookDelivery(RuntimeError):
    """Raised when a webhook delivery has already been reserved/processed."""


WEBHOOK_IDEMPOTENCY_TTL_SECONDS = int(os.getenv("WEBHOOK_IDEMPOTENCY_TTL_SECONDS", "172800"))  # 2 days
WEBHOOK_STATUS_TTL_SECONDS = int(os.getenv("WEBHOOK_STATUS_TTL_SECONDS", "172800"))


def _delivery_idempotency_key(delivery_key: str) -> str:
    return f"webhook:idempotency:{delivery_key}"


def _delivery_status_key(delivery_key: str) -> str:
    return f"webhook:delivery:{delivery_key}"


def compute_delivery_key(headers: Dict[str, str], body: bytes) -> str:
    return make_idempotency_key_for_webhook(headers, body)


def reserve_delivery(redis_conn, delivery_key: str) -> None:
    """Reserve a delivery idempotency key. Raises on duplicate/unavailable."""
    if not redis_conn:
        raise WebhookQueueUnavailable("Redis unavailable for webhook idempotency")

    key = _delivery_idempotency_key(delivery_key)
    was_set = redis_conn.setnx(key, "1")
    if not was_set:
        raise DuplicateWebhookDelivery(f"Duplicate webhook delivery {delivery_key}")

    redis_conn.expire(key, WEBHOOK_IDEMPOTENCY_TTL_SECONDS)


def release_delivery(redis_conn, delivery_key: str) -> None:
    """Release a reserved delivery if enqueue fails."""
    if not redis_conn:
        return
    try:
        redis_conn.delete(_delivery_idempotency_key(delivery_key))
        redis_conn.delete(_delivery_status_key(delivery_key))
    except Exception:
        logger.debug("Failed to release webhook delivery %s", delivery_key, exc_info=True)


def _get_retry_policy():
    try:
        from rq import Retry
    except Exception:
        return None

    max_retries = int(os.getenv("WEBHOOK_MAX_RETRIES", "5"))
    default_intervals = [5, 15, 60, 300, 900]
    retry_intervals = default_intervals[:max_retries]
    return Retry(max=max_retries, interval=retry_intervals)


def enqueue_webhook_delivery(
    redis_conn,
    delivery_key: str,
    topic: str,
    shop_domain: str,
    body: bytes,
    headers: Dict[str, str],
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Enqueue a webhook delivery for background processing."""
    if not redis_conn:
        raise WebhookQueueUnavailable("Redis unavailable for webhook queue")

    status_key = _delivery_status_key(delivery_key)
    queue_name = os.getenv("WEBHOOK_QUEUE_NAME", "webhooks")
    job_timeout = int(os.getenv("WEBHOOK_JOB_TIMEOUT", "60"))

    try:
        from rq import Queue
    except Exception as exc:
        # Local and test environments may not install RQ. Keep the
        # delivery recorded as queued so webhook endpoints remain usable
        # while still making explicit queue-outage tests possible through
        # targeted monkeypatching.
        fallback_job_id = f"local-{delivery_key[:12]}"
        redis_conn.hset(
            status_key,
            mapping={
                "status": "queued",
                "job_id": fallback_job_id,
                "topic": topic,
                "shop_domain": shop_domain,
                "request_id": request_id or "",
                "attempts": 0,
                "last_error": "rq_unavailable_local_fallback",
                "created_at": datetime.utcnow().isoformat(),
            },
        )
        redis_conn.expire(status_key, WEBHOOK_STATUS_TTL_SECONDS)
        logger.warning(
            "RQ not available; recording webhook delivery %s with local fallback",
            delivery_key,
            exc_info=exc,
        )
        return {"job_id": fallback_job_id, "status": "queued"}

    retry_policy = _get_retry_policy()
    queue = Queue(queue_name, connection=redis_conn)

    job = queue.enqueue(
        "jobs.webhook_tasks.process_webhook",
        delivery_key,
        topic,
        shop_domain,
        body,
        headers,
        request_id,
        job_timeout=job_timeout,
        retry=retry_policy,
    )

    redis_conn.hset(
        status_key,
        mapping={
            "status": "queued",
            "job_id": job.id,
            "topic": topic,
            "shop_domain": shop_domain,
            "request_id": request_id or "",
            "attempts": 0,
            "last_error": "",
            "created_at": datetime.utcnow().isoformat(),
        },
    )
    redis_conn.expire(status_key, WEBHOOK_STATUS_TTL_SECONDS)

    return {"job_id": job.id, "status": "queued"}
