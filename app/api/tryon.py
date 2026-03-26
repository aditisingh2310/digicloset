from __future__ import annotations

import asyncio
import html
import threading
from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/try-on", tags=["try-on"])


class TryOnGenerateRequest(BaseModel):
    user_image_url: str = Field(..., min_length=1)
    garment_image_url: str = Field(..., min_length=1)
    product_id: str = Field("demo-product", min_length=1)
    category: str = Field("upper_body", min_length=1)


def _jobs(request: Request) -> Dict[str, Dict[str, Any]]:
    jobs = getattr(request.app.state, "tryon_jobs", None)
    if jobs is None:
        jobs = {}
        request.app.state.tryon_jobs = jobs
    return jobs


def _merchant_state(request: Request) -> Dict[str, Dict[str, Any]]:
    state = getattr(request.app.state, "dev_merchant_state", None)
    if state is None:
        state = {}
        request.app.state.dev_merchant_state = state
    return state


def _build_svg_preview(job: Dict[str, Any]) -> str:
    user_image_url = html.escape(job["user_image_url"], quote=True)
    garment_image_url = html.escape(job["garment_image_url"], quote=True)
    product_id = html.escape(job["product_id"], quote=True)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 1200" role="img" aria-label="DigiCloset try-on preview">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#f8faf8"/>
      <stop offset="100%" stop-color="#edf3ef"/>
    </linearGradient>
    <clipPath id="frame">
      <rect x="54" y="150" width="792" height="920" rx="38" ry="38"/>
    </clipPath>
    <clipPath id="garmentFrame">
      <rect x="275" y="338" width="350" height="470" rx="28" ry="28"/>
    </clipPath>
  </defs>
  <rect width="900" height="1200" fill="url(#bg)"/>
  <text x="68" y="84" font-size="24" font-family="Segoe UI, Arial, sans-serif" letter-spacing="4" fill="#73583b">DIGICLOSET PREVIEW</text>
  <text x="68" y="118" font-size="52" font-weight="700" font-family="Segoe UI, Arial, sans-serif" fill="#13212f">Virtual try-on result</text>
  <rect x="54" y="150" width="792" height="920" rx="38" ry="38" fill="#ffffff" stroke="rgba(15,23,42,0.10)"/>
  <image href="{user_image_url}" x="54" y="150" width="792" height="920" preserveAspectRatio="xMidYMid slice" clip-path="url(#frame)"/>
  <rect x="252" y="314" width="396" height="518" rx="36" ry="36" fill="rgba(255,255,255,0.72)" stroke="rgba(19,33,47,0.10)"/>
  <image href="{garment_image_url}" x="275" y="338" width="350" height="470" preserveAspectRatio="xMidYMid meet" clip-path="url(#garmentFrame)" opacity="0.9"/>
  <rect x="92" y="994" width="716" height="46" rx="23" ry="23" fill="rgba(255,255,255,0.92)" stroke="rgba(19,33,47,0.10)"/>
  <text x="116" y="1024" font-size="22" font-family="Segoe UI, Arial, sans-serif" fill="#44505c">Product: {product_id}</text>
</svg>"""


async def _process_tryon_job(app, shop: str, job_id: str) -> None:
    jobs = getattr(app.state, "tryon_jobs", {})
    job = jobs.get(job_id)
    if not job:
        return

    started = datetime.utcnow()

    try:
        await asyncio.sleep(0.35)
        job["status"] = "processing"

        await asyncio.sleep(0.9)
        completed = datetime.utcnow()
        processing_seconds = max(1, int((completed - started).total_seconds()))
        image_url = f"/api/v1/try-on/{job_id}/image"

        job.update(
            {
                "status": "completed",
                "image_url": image_url,
                "generated_image_url": image_url,
                "processing_time": processing_seconds,
                "generation_time": processing_seconds * 1000,
                "completed_at": completed.isoformat(),
            }
        )

        if getattr(app.state, "redis", None):
            history_entry = {
                "id": job_id,
                "status": "completed",
                "product_id": job["product_id"],
                "image_url": image_url,
                "created_at": job["created_at"],
            }
            try:
                app.state.redis.set(f"merchant:{shop}:widget_enabled", "true")
                app.state.redis.set(f"merchant:{shop}:tryons_generated", str(int(app.state.redis.get(f"merchant:{shop}:tryons_generated") or 0) + 1))
                app.state.redis.set(f"merchant:{shop}:credits_used", str(int(app.state.redis.get(f"merchant:{shop}:credits_used") or 0) + 1))
                app.state.redis.rpush(f"merchant:{shop}:generation_history", __import__("json").dumps(history_entry))
            except Exception:
                pass

        dev_state = getattr(app.state, "dev_merchant_state", None)
        if dev_state is not None:
            merchant = dev_state.setdefault(
                shop,
                {
                    "tryons_generated": 0,
                    "credits_used": 0,
                    "generation_history": [],
                    "widget_enabled": True,
                },
            )
            merchant["tryons_generated"] += 1
            merchant["credits_used"] += 1
            merchant["widget_enabled"] = True
            merchant["generation_history"] = [
                {
                    "id": job_id,
                    "status": "completed",
                    "product_id": job["product_id"],
                    "image_url": image_url,
                    "created_at": job["created_at"],
                },
                *merchant.get("generation_history", []),
            ][:20]

        store = getattr(app.state, "store", None)
        if store is not None:
            from app.services.billing_service import BillingService

            service = BillingService(shop, "", store)
            await service.increment_usage(ai_calls=1)
    except Exception as exc:
        job["status"] = "failed"
        job["error"] = str(exc)


@router.post("/generate")
async def generate_tryon(payload: TryOnGenerateRequest, request: Request) -> Dict[str, Any]:
    tenant = getattr(request.state, "tenant", None)
    if tenant is None:
        raise HTTPException(status_code=401, detail="Missing tenant")

    if not payload.user_image_url or not payload.garment_image_url:
        raise HTTPException(status_code=400, detail="Missing try-on image payload")

    job_id = str(uuid4())
    jobs = _jobs(request)
    jobs[job_id] = {
        "id": job_id,
        "job_id": job_id,
        "shop": tenant.shop_domain,
        "status": "pending",
        "product_id": payload.product_id,
        "category": payload.category,
        "user_image_url": payload.user_image_url,
        "garment_image_url": payload.garment_image_url,
        "created_at": datetime.utcnow().isoformat(),
        "error": None,
    }

    threading.Thread(
        target=lambda: asyncio.run(_process_tryon_job(request.app, tenant.shop_domain, job_id)),
        daemon=True,
    ).start()

    return {
        "id": job_id,
        "job_id": job_id,
        "status": "pending",
        "created_at": jobs[job_id]["created_at"],
    }


@router.get("/history")
async def tryon_history(request: Request, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
    tenant = getattr(request.state, "tenant", None)
    if tenant is None:
        raise HTTPException(status_code=401, detail="Missing tenant")

    jobs = [
        job
        for job in _jobs(request).values()
        if job.get("shop") == tenant.shop_domain
    ]
    jobs.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    page = jobs[offset : offset + min(limit, 100)]

    return {
        "tryons": [
            {
                "id": job["id"],
                "status": job["status"],
                "product_id": job["product_id"],
                "image_url": job.get("image_url"),
                "created_at": job["created_at"],
            }
            for job in page
        ],
        "total": len(jobs),
        "limit": limit,
        "offset": offset,
    }


@router.get("/{tryon_id}/image")
async def tryon_image(tryon_id: str, request: Request) -> Response:
    tenant = getattr(request.state, "tenant", None)
    if tenant is None:
        raise HTTPException(status_code=401, detail="Missing tenant")

    job = _jobs(request).get(tryon_id)
    if not job:
        raise HTTPException(status_code=404, detail="Try-on not found")
    if job.get("shop") != tenant.shop_domain:
        raise HTTPException(status_code=403, detail="Try-on does not belong to this tenant")

    if job.get("status") != "completed":
        raise HTTPException(status_code=409, detail="Try-on result not ready")

    return Response(content=_build_svg_preview(job), media_type="image/svg+xml")


@router.get("/{tryon_id}")
async def tryon_status(tryon_id: str, request: Request) -> Dict[str, Any]:
    tenant = getattr(request.state, "tenant", None)
    if tenant is None:
        raise HTTPException(status_code=401, detail="Missing tenant")

    job = _jobs(request).get(tryon_id)
    if not job:
        raise HTTPException(status_code=404, detail="Try-on not found")
    if job.get("shop") != tenant.shop_domain:
        raise HTTPException(status_code=403, detail="Try-on does not belong to this tenant")

    return {
        "id": job["id"],
        "job_id": job["job_id"],
        "status": job["status"],
        "image_url": job.get("image_url"),
        "generated_image_url": job.get("generated_image_url"),
        "processing_time": job.get("processing_time"),
        "generation_time": job.get("generation_time"),
        "error": job.get("error"),
        "created_at": job["created_at"],
    }
