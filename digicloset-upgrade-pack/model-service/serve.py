
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import uuid
import os
import shutil
from typing import Optional

from app.core.config import settings
from app.services.inference_provider import ProviderFactory
from app.evaluation.harness import evaluation_harness

app = FastAPI(title=settings.APP_NAME)

@app.post('/predict')
async def predict(
    user_image: UploadFile = File(...), 
    garment_image: Optional[UploadFile] = File(None)
):
    try:
        # Read images
        user_bytes = await user_image.read()
        garment_bytes = await garment_image.read() if garment_image else None
        
        # Get Provider (with fallback logic)
        provider = ProviderFactory.get_provider()
        
        # Generate
        result = await provider.generate(
            user_image=user_bytes, 
            garment_image=garment_bytes,
            steps=settings.DEFAULT_STEPS,
            resolution=settings.DEFAULT_RESOLUTION
        )
        
        # In a real scenario, we would decode the base64 image here and run evaluation
        # For this stub, we just log the attempt
        # evaluation_harness.log_experiment(...)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/')
def root():
    return {
        "message": "Model Service Running", 
        "provider": settings.INFERENCE_PROVIDER,
        "debug": settings.DEBUG
    }
