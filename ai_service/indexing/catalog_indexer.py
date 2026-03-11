"""Shopify catalog indexing for product embeddings."""

import asyncio
import logging
from typing import Dict, List, Optional
import numpy as np
from ..embeddings import CLIPEmbedder
from ..vector_db import ProductVectorIndex
from ..utils import ImageLoader, download_image

logger = logging.getLogger(__name__)


class CatalogIndexer:
    """
    Indexes Shopify products into FAISS vector database.
    
    Handles:
    - Image downloading
    - Multimodal embedding generation
    - Metadata storage
    - Error handling and fallbacks
    """
    
    def __init__(
        self,
        embedder: CLIPEmbedder,
        vector_index: ProductVectorIndex,
        image_loader: Optional[ImageLoader] = None
    ):
        """
        Initialize catalog indexer.
        
        Args:
            embedder: CLIPEmbedder instance
            vector_index: ProductVectorIndex instance
            image_loader: ImageLoader instance (created if None)
        """
        self.embedder = embedder
        self.vector_index = vector_index
        self.image_loader = image_loader or ImageLoader()
        self.failed_products = []
    
    def index_product(
        self,
        product: Dict,
        skip_image_errors: bool = True
    ) -> bool:
        """
        Index a single product.
        
        Product format:
        {
            "id": int,
            "title": str,
            "description": str,
            "image_url": str,
            "category": str,
            "tags": list[str]
        }
        
        Args:
            product: Product data
            skip_image_errors: If True, generate embedding from text if image fails
            
        Returns:
            True if successful, False otherwise
        """
        try:
            product_id = product["id"]
            
            # Download image if URL provided
            image = None
            if product.get("image_url"):
                image = self.image_loader.load_from_url(product["image_url"])
                if image:
                    image = self.image_loader.preprocess(image)
            
            # Fallback: Use text-only embedding if image unavailable
            if image is None and not skip_image_errors:
                logger.warning(f"Product {product_id}: Image unavailable, skipping")
                self.failed_products.append(
                    {"product_id": product_id, "reason": "image_unavailable"}
                )
                return False
            
            # Generate embedding
            embedding, sources = self.embedder.embed_product(
                image=image,
                title=product.get("title"),
                description=product.get("description", "")
            )
            
            # Prepare metadata
            metadata = {
                "title": product.get("title"),
                "description": product.get("description", ""),
                "category": product.get("category", ""),
                "tags": product.get("tags", []),
                "image_url": product.get("image_url"),
                "embedding_sources": sources
            }
            
            # Add to index
            self.vector_index.add_product(product_id, embedding, metadata)
            logger.debug(f"Indexed product {product_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to index product {product.get('id')}: {e}")
            self.failed_products.append(
                {"product_id": product.get("id"), "reason": str(e)}
            )
            return False
    
    def batch_index(
        self,
        products: List[Dict],
        skip_image_errors: bool = True,
        batch_size: int = 32
    ) -> Dict:
        """
        Index multiple products efficiently.
        
        Args:
            products: List of product dicts
            skip_image_errors: Skip images that fail to download
            batch_size: Batch size for processing
            
        Returns:
            Statistics dict with counts and failed products
        """
        self.failed_products = []
        successful = 0
        total = len(products)
        
        logger.info(f"Starting batch indexing of {total} products")
        
        for i in range(0, total, batch_size):
            batch = products[i:i + batch_size]
            batch_success = 0
            
            for product in batch:
                if self.index_product(product, skip_image_errors):
                    batch_success += 1
            
            successful += batch_success
            logger.info(
                f"Progress: {i + batch_size}/{total} "
                f"(batch: {batch_success}/{len(batch)})"
            )
        
        stats = {
            "total": total,
            "successful": successful,
            "failed": len(self.failed_products),
            "failed_products": self.failed_products,
            "index_size": self.vector_index.get_size()
        }
        
        logger.info(
            f"Indexing complete: {successful}/{total} successful, "
            f"index size: {stats['index_size']}"
        )
        
        return stats


async def index_shopify_catalog(
    products: List[Dict],
    embedder: CLIPEmbedder,
    vector_index: ProductVectorIndex,
    batch_size: int = 32
) -> Dict:
    """
    Index a Shopify catalog (async-friendly wrapper).
    
    Args:
        products: List of product dicts
        embedder: CLIPEmbedder instance
        vector_index: ProductVectorIndex instance
        batch_size: Batch size for processing
        
    Returns:
        Indexing statistics
    """
    indexer = CatalogIndexer(embedder, vector_index)
    
    # Run in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    stats = await loop.run_in_executor(
        None,
        lambda: indexer.batch_index(products, batch_size=batch_size)
    )
    
    return stats
