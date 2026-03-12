import logging
import os
import json
from typing import Dict, Any

from app.ai.services.ai_service import AIService
from app.ai.services.ai_with_cb import AIServiceWithCircuitBreaker
from jobs.redis_conn import get_redis_connection

logger = logging.getLogger(__name__)

_ai_service: AIServiceWithCircuitBreaker | None = None


def get_ai_service() -> AIServiceWithCircuitBreaker:
    global _ai_service
    if _ai_service is None:
        model = os.getenv("AI_MODEL_NAME", None)
        base = AIService(model_name=model)
        _ai_service = AIServiceWithCircuitBreaker(
            base,
            failure_threshold=int(os.getenv("AI_CB_FAILURE_THRESHOLD", "3")),
            reset_timeout=float(os.getenv("AI_CB_RESET_TIMEOUT", "30")),
            timeout=float(os.getenv("AI_INFERENCE_TIMEOUT", "5")),
        )
    return _ai_service


def _update_job_state(job_id: str, status: str, result: Dict[str, Any] | None = None, error: str = "") -> None:
    try:
        conn = get_redis_connection()
        payload = {"status": status, "error": error, "result": json.dumps(result) if result else ""}
        conn.hset(f"job_status:{job_id}", mapping=payload)
        conn.expire(f"job_status:{job_id}", 86400)
    except Exception:
        logger.debug("Failed to persist job state for %s", job_id, exc_info=True)


def process_inference(prompt: str, max_tokens: int = 128) -> Dict[str, Any]:
    """RQ worker entry point with retry-safe status tracking and DLQ recording."""
    from rq import get_current_job
    import asyncio

    job = get_current_job()
    job_id = job.id if job else "unknown"
    _update_job_state(job_id, "processing")

    ai = get_ai_service()
    try:
        result = asyncio.run(ai.infer(prompt, max_tokens=max_tokens, timeout=float(os.getenv("AI_INFERENCE_TIMEOUT", "30"))))
        _update_job_state(job_id, "completed", result=result)
        return result
    except Exception as exc:
        logger.exception("Inference job failed: %s", exc)
        retries_left = 0
        if job and job.retries_left is not None:
            retries_left = int(job.retries_left)

        _update_job_state(job_id, "failed", error=str(exc))
        if retries_left <= 0:
            try:
                conn = get_redis_connection()
                conn.rpush(
                    "ai:dead_letter",
                    json.dumps({"job_id": job_id, "prompt": prompt[:500], "max_tokens": max_tokens, "error": str(exc)}),
                )
            except Exception:
                logger.debug("Failed to write DLQ record", exc_info=True)
        raise
