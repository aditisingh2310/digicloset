from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import httpx
import os
from app.services.stylist_service import generate_cross_sell_query

router = APIRouter()

EMBEDDING_SEARCH_URL = os.getenv("EMBEDDING_SEARCH_URL", "http://model-service:8001/embeddings/search")
EMBEDDING_TEXT_SEARCH_URL = os.getenv("EMBEDDING_TEXT_SEARCH_URL", "http://model-service:8001/embeddings/search-text")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/digicloset_uploads")

from pydantic import BaseModel

RANKING_RANK_URL = os.getenv("RANKING_RANK_URL", "http://model-service:8001/ranking/rank")
RANKING_INTERACTION_URL = os.getenv("RANKING_INTERACTION_URL", "http://model-service:8001/ranking/interaction")

@router.get("/{item_id}/cross-sell")
async def get_cross_sell_recommendations(item_id: str, top_k: int = 5):
    """
    Given a locally stored garment image, uses a Vision LLM to deduce complementary styling 
    options, tracking down the exact vector neighbors in FAISS via text-to-image semantic search.
    """
    image_path = os.path.join(UPLOAD_DIR, item_id)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Garment image not found locally to analyze")

    try:
        # Load local image to analyze stylistically
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        # Step 1: Let the LLM Vision model write the search query (e.g. 'dark denim jacket')
        stylist_text_query = await generate_cross_sell_query(image_bytes)

        # Step 2: Use the newly appended query to execute text-to-image AI search
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{EMBEDDING_TEXT_SEARCH_URL}",
                params={"query": stylist_text_query, "top_k": top_k},
                timeout=15.0
            )

            if r.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Model service error parsing text: {r.text}")

            data = r.json()
            similar_items = data.get("results", [])

            return {
                "base_item_id": item_id, 
                "generated_outfit_query": stylist_text_query,
                "complementary_items": similar_items
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cross-sell generation failed: {str(e)}")

@router.get("/{item_id}/similar")
async def get_similar_garments(item_id: str, top_k: int = 5, user_id: str = None):
    """
    Finds semantically similar garments by querying the model-service FAISS vector database.
    If a user_id is provided, candidates are re-ranked using the user's personalization profile.
    """
    image_path = os.path.join(UPLOAD_DIR, item_id)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Garment image not found locally to query")

    try:
        # Load local image to use as the visual search query
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        async with httpx.AsyncClient() as client:
            files = {'image': (item_id, image_bytes, 'image/jpeg')}
            r = await client.post(
                f"{EMBEDDING_SEARCH_URL}?top_k={top_k}", 
                files=files, 
                timeout=15.0
            )
            
            if r.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Model service error: {r.text}")
                
            data = r.json()
            similar_items = data.get("results", [])
            
            # If user context provided, personalize the search results
            if user_id and similar_items:
                rank_payload = {
                    "user_id": user_id,
                    "candidates": similar_items,
                    "alpha": 0.7  # 70% FAISS score, 30% User Profile score
                }
                rank_res = await client.post(RANKING_RANK_URL, json=rank_payload, timeout=10.0)
                if rank_res.status_code == 200:
                    similar_items = rank_res.json().get("results", similar_items)
            
            return {"query_id": item_id, "similar_items": similar_items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch similar items: {str(e)}")

class InteractionPayload(BaseModel):
    user_id: str
    weight: float = 0.5  # 0.1 for view, 0.5 for like, 1.0 for try-on

@router.post("/{item_id}/interact")
async def record_interaction(item_id: str, payload: InteractionPayload):
    """
    Record user interaction to build a personalization semantic profile.
    """
    try:
        async with httpx.AsyncClient() as client:
            interaction_data = {
                "user_id": payload.user_id,
                "item_id": item_id,
                "weight": payload.weight
            }
            r = await client.post(RANKING_INTERACTION_URL, json=interaction_data, timeout=5.0)
            if r.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Model service error: {r.text}")
            return r.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record interaction: {str(e)}")

COLOR_EXTRACT_URL = os.getenv("COLOR_EXTRACT_URL", "http://model-service:8001/colors/extract")

@router.get("/{item_id}/colors")
async def get_garment_colors(item_id: str, num_colors: int = 3):
    """
    Extracts the dominant fashion colors of a garment by querying the model-service.
    """
    image_path = os.path.join(UPLOAD_DIR, item_id)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Garment image not found locally to query")

    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        async with httpx.AsyncClient() as client:
            files = {'image': (item_id, image_bytes, 'image/jpeg')}
            r = await client.post(
                f"{COLOR_EXTRACT_URL}?num_colors={num_colors}", 
                files=files, 
                timeout=10.0
            )
            
            if r.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Model service error: {r.text}")
                
            data = r.json()
            return {"query_id": item_id, "colors": data.get("colors", [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract colors: {str(e)}")

BG_REMOVAL_URL = os.getenv("BG_REMOVAL_URL", "http://model-service:8001/images/remove-bg")

@router.post("/{item_id}/remove-bg")
async def remove_garment_background(item_id: str, bg_color: str = None):
    """
    Strips the background of a garment using the AI model-service.
    Overwrites the local image with a transparent PNG or solid composite.
    """
    image_path = os.path.join(UPLOAD_DIR, item_id)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Garment image not found locally")

    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        async with httpx.AsyncClient() as client:
            files = {'image': (item_id, image_bytes, 'image/jpeg')}
            params = {}
            if bg_color:
                params['bg_color'] = bg_color
                
            r = await client.post(
                BG_REMOVAL_URL, 
                files=files, 
                params=params,
                timeout=30.0 # Background removal can take a few seconds
            )
            
            if r.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Model service error: {r.text}")
                
            # Overwrite local file with the new cleaned image
            with open(image_path, "wb") as f:
                f.write(r.content)
                
            return {"status": "success", "message": "Background cleanly removed", "item_id": item_id}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove background: {str(e)}")
