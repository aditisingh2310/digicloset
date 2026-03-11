"""FastAPI routes for recommendation API."""

import logging
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Request/Response models
class ProductInput(BaseModel):
    """Product input format."""
    id: int
    title: str
    description: Optional[str] = ""
    image_url: Optional[str] = None
    category: str
    tags: List[str] = Field(default_factory=list)


class IndexRequest(BaseModel):
    """Request to index products."""
    products: List[ProductInput]
    batch_size: int = Field(default=32, ge=1, le=256)


class IndexResponse(BaseModel):
    """Response from indexing."""
    total: int
    successful: int
    failed: int
    index_size: int
    failed_products: Optional[List[Dict]] = None


class RecommendationResponse(BaseModel):
    """Single product recommendation."""
    product_id: int
    title: Optional[str] = None
    category: Optional[str] = None
    similarity: Optional[float] = None
    outfit_score: Optional[float] = None
    compatibility_score: Optional[float] = None


class RecommendationsListResponse(BaseModel):
    """List of recommendations."""
    query_product_id: int
    recommendations: List[RecommendationResponse]
    total_count: int


class OutfitResponse(BaseModel):
    """Complete outfit response."""
    base_product_id: int
    base_category: str
    total_items: int
    outfit_score: float
    outfit_items: List[Dict]


def create_router(embedder, vector_index, recommender):
    """
    Create FastAPI router with all endpoints.
    
    Args:
        embedder: CLIPEmbedder instance
        vector_index: ProductVectorIndex instance
        recommender: Recommender instance
        
    Returns:
        APIRouter with all routes
    """
    router = APIRouter(prefix="/api/v1", tags=["recommendations"])
    
    @router.post(
        "/index-catalog",
        response_model=IndexResponse,
        summary="Index Shopify catalog",
        description="Index products into the recommendation engine"
    )
    async def index_catalog(
        request: IndexRequest,
        background_tasks: BackgroundTasks
    ):
        """
        Index a catalog of products.
        
        Can run synchronously or asynchronously in background.
        """
        try:
            if not request.products:
                raise HTTPException(status_code=400, detail="Empty product list")
            
            # Convert to dict format
            products = [p.model_dump() for p in request.products]
            
            logger.info(f"Starting indexing of {len(products)} products")
            
            # Run indexing in background
            from ..indexing import CatalogIndexer
            
            indexer = CatalogIndexer(embedder, vector_index)
            stats = indexer.batch_index(
                products,
                skip_image_errors=True,
                batch_size=request.batch_size
            )
            
            logger.info(f"Indexing complete: {stats['successful']}/{stats['total']}")
            
            return IndexResponse(
                total=stats["total"],
                successful=stats["successful"],
                failed=stats["failed"],
                index_size=stats["index_size"],
                failed_products=stats.get("failed_products")[:10]  # Limit output
            )
        
        except Exception as e:
            logger.error(f"Indexing error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get(
        "/recommend/similar",
        response_model=RecommendationsListResponse,
        summary="Find visually similar products",
        description="Returns products with similar embeddings"
    )
    async def recommend_similar(
        product_id: int = Query(..., gt=0),
        top_k: int = Query(10, ge=1, le=50),
        exclude_category: bool = Query(False)
    ):
        """Find visually similar products."""
        try:
            if vector_index.get_size() == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Catalog not indexed. Please index products first."
                )
            
            # For now, return search results
            metadata = vector_index.get_metadata(product_id)
            if not metadata:
                raise HTTPException(status_code=404, detail="Product not found")
            
            # Get similar products via recommender
            recommendations = recommender.recommend_similar_products(
                product_id,
                top_k=top_k,
                exclude_category=exclude_category
            )
            
            return RecommendationsListResponse(
                query_product_id=product_id,
                recommendations=[
                    RecommendationResponse(
                        product_id=item["product_id"],
                        title=item.get("title"),
                        category=item.get("category"),
                        similarity=item.get("similarity")
                    )
                    for item in recommendations
                ],
                total_count=len(recommendations)
            )
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Recommendation error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get(
        "/recommend/style",
        response_model=RecommendationsListResponse,
        summary="Find style-compatible items",
        description="Returns compatible items in different categories"
    )
    async def recommend_style(
        product_id: int = Query(..., gt=0),
        top_k: int = Query(5, ge=1, le=30)
    ):
        """Find style-complementary products."""
        try:
            if vector_index.get_size() == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Catalog not indexed"
                )
            
            metadata = vector_index.get_metadata(product_id)
            if not metadata:
                raise HTTPException(status_code=404, detail="Product not found")
            
            recommendations = recommender.recommend_style_matches(
                product_id,
                top_k=top_k
            )
            
            return RecommendationsListResponse(
                query_product_id=product_id,
                recommendations=[
                    RecommendationResponse(
                        product_id=item["product_id"],
                        title=item.get("title"),
                        category=item.get("category"),
                        compatibility_score=item.get("compatibility_score")
                    )
                    for item in recommendations
                ],
                total_count=len(recommendations)
            )
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Style recommendation error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get(
        "/recommend/outfit",
        response_model=OutfitResponse,
        summary="Complete the look outfit",
        description="Suggests complementary items to complete an outfit"
    )
    async def recommend_outfit(
        product_id: int = Query(..., gt=0),
        max_items: int = Query(4, ge=2, le=8)
    ):
        """Get outfit completion recommendations."""
        try:
            if vector_index.get_size() == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Catalog not indexed"
                )
            
            metadata = vector_index.get_metadata(product_id)
            if not metadata:
                raise HTTPException(status_code=404, detail="Product not found")
            
            outfit = recommender.recommend_complete_outfit(
                product_id,
                max_items=max_items
            )
            
            if "error" in outfit:
                raise HTTPException(status_code=404, detail=outfit["error"])
            
            return OutfitResponse(**outfit)
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Outfit recommendation error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get(
        "/health",
        summary="Health check",
        description="Check service health and index status"
    )
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "indexed_products": vector_index.get_size(),
            "model": embedder.model_name,
            "device": embedder.device
        }
    
    return router
