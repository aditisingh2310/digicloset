from fastapi import APIRouter, Depends, HTTPException
from typing import Dict
import asyncio
import json
import os

from app.ai.schemas import AIRequest, AIResponse
from app.core.config import settings
from fastapi import status

try:
    from rq import Queue, Retry
    from rq.job import Job
except Exception:
    Queue = None
    Retry = None
    Job = None

from jobs.redis_conn import get_redis_connection

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/infer", response_model=AIResponse)
async def infer_endpoint(body: AIRequest, app=Depends(lambda: None)) -> Dict:
    """Direct inference endpoint (backwards compatible)."""
    try:
        from app.main import app as fastapi_app
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Application not initialized")

    ai_service = getattr(fastapi_app.state, "ai_service", None)
    if ai_service is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service not available")

    try:
        result = await asyncio.wait_for(ai_service.infer(body.prompt, max_tokens=body.max_tokens), timeout=settings.ai_inference_timeout)
        return AIResponse(**result)
    except asyncio.TimeoutError:
        return AIResponse(text="The AI service timed out. Please try again later.", confidence=0.0)
    except Exception:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI_inference_failed")


@router.post("/process")
def enqueue_inference(body: AIRequest) -> Dict:
    """Enqueue an AI inference job and return immediately with a job_id."""
    conn = get_redis_connection()
    if Queue is None:
        raise HTTPException(status_code=503, detail="Background queue not configured")

    q = Queue("ai", connection=conn)
    job_timeout = int(body.max_tokens) * 2 if body.max_tokens else 60
    max_retries = int(os.getenv("AI_JOB_MAX_RETRIES", "3"))
    retry_policy = Retry(max=max_retries, interval=[5, 15, 30]) if Retry else None

    job = q.enqueue(
        "jobs.ai_tasks.process_inference",
        body.prompt,
        body.max_tokens,
        job_timeout=job_timeout,
        retry=retry_policy,
    )

    conn.hset(f"job_status:{job.id}", mapping={"status": "pending", "error": "", "result": ""})
    conn.expire(f"job_status:{job.id}", 86400)
    return {"job_id": job.id, "status": "pending"}


@router.get("/status/{job_id}")
def job_status(job_id: str) -> Dict:
    """Return job status in production state vocabulary."""
    conn = get_redis_connection()
    if Job is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Background job support not available")

    cached = conn.hgetall(f"job_status:{job_id}") if conn else {}
    if cached:
        result = json.loads(cached["result"]) if cached.get("result") else None
        return {"status": cached.get("status", "pending"), "result": result, "error": cached.get("error") or None}

    try:
        job = Job.fetch(job_id, connection=conn)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    status_map = {
        "queued": "pending",
        "deferred": "pending",
        "started": "processing",
        "finished": "completed",
        "failed": "failed",
    }
    state = job.get_status()
    res = job.result if state == "finished" else None
    err = getattr(job, "exc_info", None) if state == "failed" else None
    return {"status": status_map.get(state, state), "result": res, "error": err}
