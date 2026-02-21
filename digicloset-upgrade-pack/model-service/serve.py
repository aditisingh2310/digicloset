from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uuid
import os
import shutil
from typing import Optional, List

from app.core.config import settings
from app.services.inference_provider import ProviderFactory
from app.evaluation.harness import evaluation_harness
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore
from app.services.color_extractor import ColorExtractor
from app.services.ranking_service import RankingService
from app.services.bg_removal_service import BackgroundRemovalService
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME)

# Initialize global services lazily to avoid blocking import
embedding_service = None
vector_store = None
color_extractor = None
ranking_service = None
bg_removal_service = None

# Pydantic models for incoming requests
class InteractionRequest(BaseModel):
    user_id: str
    item_id: str
    weight: float = 0.5

class Candidate(BaseModel):
    id: str
    score: float

class RankRequest(BaseModel):
    user_id: str
    candidates: List[Candidate]
    alpha: float = 0.7

@app.on_event("startup")
async def startup_event():
    global embedding_service, vector_store, color_extractor, ranking_service, bg_removal_service
    logger.info("Initializing ML Services...")
    embedding_service = EmbeddingService()
    vector_store = VectorStore()
    color_extractor = ColorExtractor()
    ranking_service = RankingService(vector_store)
    # Lazy-load to avoid large startup lockups during container spin-up
    bg_removal_service = BackgroundRemovalService()

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
        
        # Convert bytes to base64 for JSON serialization
        if "image_bytes" in result and result["image_bytes"]:
            import base64
            result["image_base64"] = base64.b64encode(result["image_bytes"]).decode('utf-8')
            del result["image_bytes"]
            
        return JSONResponse(content=result)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/')
def root():
    return {
        "message": "Model Service Running", 
        "provider": settings.INFERENCE_PROVIDER,
        "debug": settings.DEBUG,
        "embeddings_active": embedding_service is not None
    }

from pydantic import BaseModel

@app.post('/embeddings/generate')
async def generate_embedding(image: UploadFile = File(...)):
    """Generate and return a 512d OpenCLIP vector for an image."""
    try:
        image_bytes = await image.read()
        vector = embedding_service.generate_embedding(image_bytes)
        return JSONResponse(content={"embedding": vector})
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/embeddings/add')
async def add_embedding(
    item_id: str,
    image: UploadFile = File(...)
):
    """Generate an embedding for the image and permanently store it in FAISS with the given item_id."""
    try:
        image_bytes = await image.read()
        vector = embedding_service.generate_embedding(image_bytes)
        vector_store.add_item(item_id, vector)
        return JSONResponse(content={"status": "success", "item_id": item_id, "message": "Added to Vector DB"})
    except Exception as e:
        logger.error(f"Error adding embedding: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/embeddings/search')
async def search_similar(
    image: UploadFile = File(None),
    top_k: int = 5
):
    """
    Search for similar items in the FAISS DB using a visual image query.
    """
    try:
        if not image:
            raise HTTPException(status_code=400, detail="Image query required")
            
        # 1. Generate query vector
        image_bytes = await image.read()
        query_vector = embedding_service.generate_embedding(image_bytes)
        
        # 2. Search FAISS
        results = vector_store.search_similar(query_vector, top_k=top_k)
        
        return JSONResponse(content={"results": results})
    except Exception as e:
        logger.error(f"Error searching embeddings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/embeddings/search-text')
async def search_similar_text(
    query: str,
    top_k: int = 5
):
    """
    Search for similar items in the FAISS DB using a text query (Text-to-Image semantic search).
    """
    try:
        if not query:
            raise HTTPException(status_code=400, detail="Text query required")
            
        # 1. Generate text vector
        query_vector = embedding_service.generate_text_embedding(query)
        
        # 2. Search FAISS
        similar_items = vector_store.search_similar(query_vector, top_k)
        
        return JSONResponse(content={"results": similar_items})
    except Exception as e:
        logger.error(f"Error searching text embeddings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/colors/extract')
async def extract_colors(
    image: UploadFile = File(...),
    num_colors: int = 3
):
    """
    Extracts the dominant fashion colors from the provided image using KMeans clustering.
    Returns a sorted list of colors (Hex, Name, Percentage).
    """
    if color_extractor is None:
        raise HTTPException(status_code=503, detail="Color extractor service unavailable")
        
    try:
        image_bytes = await image.read()
        colors = color_extractor.extract_colors(image_bytes, num_colors=num_colors)
        return JSONResponse(content={"colors": colors})
    except Exception as e:
        logger.error(f"Error extracting colors: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/ranking/interaction')
async def record_interaction(req: InteractionRequest):
    """
    Record a user's interaction with an item to update their personalization profile vector.
    """
    if ranking_service is None:
        raise HTTPException(status_code=503, detail="Ranking service unavailable")
        
    try:
        success = ranking_service.record_interaction(req.user_id, req.item_id, req.weight)
        if not success:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Item not found in VectorStore"})
        return JSONResponse(content={"status": "success", "message": "Profile updated"})
    except Exception as e:
        logger.error(f"Error recording interaction: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/ranking/rank')
async def rank_candidates(req: RankRequest):
    """
    Re-rank candidates using the user's personalization profile to boost similarity scores.
    """
    if ranking_service is None:
        raise HTTPException(status_code=503, detail="Ranking service unavailable")
        
    try:
        candidates_list = [{"id": c.id, "score": c.score} for c in req.candidates]
        ranked = ranking_service.rank_candidates(req.user_id, candidates_list, req.alpha)
        return JSONResponse(content={"results": ranked})
    except Exception as e:
        logger.error(f"Error ranking candidates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import Response

@app.post('/images/remove-bg')
async def remove_background(
    image: UploadFile = File(...),
    bg_color: Optional[str] = None
):
    """
    Strips the background from the provided product image.
    If bg_color is provided (e.g., '#FFFFFF'), composites the garment onto that solid color.
    Returns the raw image bytes.
    """
    if bg_removal_service is None:
        raise HTTPException(status_code=503, detail="Background removal service unavailable")
        
    try:
        image_bytes = await image.read()
        out_bytes = bg_removal_service.remove_background(image_bytes, bg_color=bg_color)
        
        media_type = "image/jpeg" if bg_color else "image/png"
        return Response(content=out_bytes, media_type=media_type)
    except Exception as e:
        logger.error(f"Error removing background: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
