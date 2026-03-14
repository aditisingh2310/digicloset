"""
AI Inference Routes

Virtual try-on generation using Replicate API
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional
import logging
import asyncio
import httpx
import os

logger = logging.getLogger(__name__)
router = APIRouter()


class GenerateTryOnRequest(BaseModel):
    """Try-on generation request"""
    user_image_url: HttpUrl
    garment_image_url: HttpUrl
    product_id: str
    category: str = "upper_body"


class PredictionResponse(BaseModel):
    """Replicate prediction response"""
    prediction_id: str
    status: str
    image_url: Optional[str] = None
    processing_time: Optional[float] = None


@router.post("/generate-tryon", response_model=dict)
async def generate_tryon(request: GenerateTryOnRequest):
    """
    Generate virtual try-on image via Replicate API.
    
    Returns immediately with prediction ID for polling.
    """
    try:
        logger.info(
            f"Try-on generation started: {request.product_id}",
            extra={
                "user_image": str(request.user_image_url)[:50],
                "category": request.category
            }
        )
        
        # Call Replicate API to create prediction
        prediction = await _create_prediction(
            str(request.user_image_url),
            str(request.garment_image_url),
            request.category
        )
        
        logger.info(
            f"Prediction created: {prediction['id']}",
            extra={"status": prediction["status"]}
        )
        
        return {
            "prediction_id": prediction["id"],
            "status": prediction["status"],
            "created_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.exception(f"Try-on generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Generation failed")


@router.get("/status/{prediction_id}", response_model=PredictionResponse)
async def get_prediction_status(prediction_id: str):
    """
    Get status of a Replicate prediction.
    
    Poll this endpoint until status is 'succeeded' or 'failed'.
    """
    try:
        logger.info(f"Checking status: {prediction_id}")
        
        status = await _get_prediction_status(prediction_id)
        
        return PredictionResponse(
            prediction_id=prediction_id,
            status=status.get("status", "unknown"),
            image_url=status.get("output", [None])[0] if status.get("output") else None
        )
    
    except Exception as e:
        logger.exception(f"Status check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Status check failed")


# ============ Replicate API Integration ============

async def _create_prediction(user_image_url: str, garment_image_url: str, category: str) -> dict:
    """Create prediction on Replicate API"""
    
    replicate_token = os.getenv("REPLICATE_API_TOKEN")
    replicate_model = os.getenv("REPLICATE_MODEL", "replicate/model:latest")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.replicate.com/v1/predictions",
            headers={
                "Authorization": f"Bearer {replicate_token}",
                "Content-Type": "application/json"
            },
            json={
                "version": replicate_model,
                "input": {
                    "user_image": user_image_url,
                    "garment_image": garment_image_url,
                    "category": category
                },
                "webhook": os.getenv("REPLICATE_WEBHOOK_URL")
            },
            timeout=30
        )
        
        if response.status_code != 201:
            logger.error(f"Replicate API error: {response.text}")
            raise Exception(f"Replicate API error: {response.status_code}")
        
        return response.json()


async def _get_prediction_status(prediction_id: str) -> dict:
    """Get prediction status from Replicate API"""
    
    replicate_token = os.getenv("REPLICATE_API_TOKEN")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.replicate.com/v1/predictions/{prediction_id}",
            headers={"Authorization": f"Bearer {replicate_token}"},
            timeout=10
        )
        
        if response.status_code != 200:
            logger.error(f"Status check failed: {response.text}")
            raise Exception("Failed to get prediction status")
        
        return response.json()


async def _poll_until_ready(prediction_id: str, timeout: int = 300, interval: int = 2) -> dict:
    """Poll prediction until complete or timeout"""
    
    start_time = asyncio.get_event_loop().time()
    
    while True:
        elapsed = asyncio.get_event_loop().time() - start_time
        
        if elapsed > timeout:
            raise TimeoutError(f"Prediction timed out after {timeout}s")
        
        status = await _get_prediction_status(prediction_id)
        
        if status.get("status") in ["succeeded", "failed"]:
            return status
        
        await asyncio.sleep(interval)
