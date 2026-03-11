"""FAISS-based vector index for product embeddings."""

import json
import logging
import os
from typing import Dict, List, Optional, Tuple
import numpy as np
import faiss

logger = logging.getLogger(__name__)


class ProductVectorIndex:
    """
    FAISS-based vector index for storing and searching product embeddings.
    
    Manages a normalized index of product embeddings with associated metadata.
    Supports fast similarity search using cosine distance.
    """

    def __init__(self, embedding_dim: int = 512):
        """
        Initialize the vector index.
        
        Args:
            embedding_dim: Dimension of embeddings
        """
        self.embedding_dim = embedding_dim
        self.index = faiss.IndexFlatL2(embedding_dim)
        self.product_ids: List[int] = []
        self.metadata: Dict[int, Dict] = {}
        
        logger.info(f"Initialized ProductVectorIndex with dimension {embedding_dim}")
    
    def add_product(
        self,
        product_id: int,
        embedding: np.ndarray,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Add a single product embedding to the index.
        
        Args:
            product_id: Shopify product ID
            embedding: Product embedding (must be float32)
            metadata: Optional metadata dict with product info
            
        Raises:
            ValueError: If embedding dimension doesn't match
        """
        if embedding.shape[0] != self.embedding_dim:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.embedding_dim}, "
                f"got {embedding.shape[0]}"
            )
        
        # Ensure float32 and 2D shape for FAISS
        embedding = embedding.astype(np.float32).reshape(1, -1)
        
        self.index.add(embedding)
        self.product_ids.append(product_id)
        
        if metadata:
            self.metadata[product_id] = metadata
        
        logger.debug(f"Added product {product_id} to index")
    
    def batch_add(
        self,
        products: List[Tuple[int, np.ndarray, Optional[Dict]]]
    ) -> None:
        """
        Add multiple products efficiently.
        
        Args:
            products: List of (product_id, embedding, metadata) tuples
        """
        if not products:
            return
        
        # Validate and prepare embeddings
        embeddings = []
        for product_id, embedding, metadata in products:
            if embedding.shape[0] != self.embedding_dim:
                logger.error(f"Skipping product {product_id}: dimension mismatch")
                continue
            
            embeddings.append(embedding.astype(np.float32))
            self.product_ids.append(product_id)
            
            if metadata:
                self.metadata[product_id] = metadata
        
        if embeddings:
            embeddings_array = np.vstack(embeddings)
            self.index.add(embeddings_array)
            logger.info(f"Batch added {len(embeddings)} products to index")
    
    def search(
        self,
        embedding: np.ndarray,
        k: int = 10
    ) -> Tuple[List[int], List[float]]:
        """
        Search for similar products using L2 distance (cosine for normalized vectors).
        
        Args:
            embedding: Query embedding (must be float32)
            k: Number of nearest neighbors to return
            
        Returns:
            Tuple of (product_ids, distances)
            
        Raises:
            ValueError: If embedding dimension doesn't match or index is empty
        """
        if len(self.product_ids) == 0:
            raise ValueError("Index is empty")
        
        if embedding.shape[0] != self.embedding_dim:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.embedding_dim}, "
                f"got {embedding.shape[0]}"
            )
        
        embedding = embedding.astype(np.float32).reshape(1, -1)
        k = min(k, len(self.product_ids))
        
        distances, indices = self.index.search(embedding, k)
        
        distances = distances[0].tolist()
        product_ids = [self.product_ids[idx] for idx in indices[0]]
        
        return product_ids, distances
    
    def search_with_metadata(
        self,
        embedding: np.ndarray,
        k: int = 10
    ) -> List[Dict]:
        """
        Search and return products with full metadata.
        
        Args:
            embedding: Query embedding
            k: Number of results
            
        Returns:
            List of dicts with 'product_id', 'distance', and metadata
        """
        product_ids, distances = self.search(embedding, k)
        
        results = []
        for prod_id, distance in zip(product_ids, distances):
            result = {
                "product_id": prod_id,
                "distance": float(distance),  # L2 distance for normalized vectors
                "similarity": 1.0 - (distance ** 2 / 2),  # Convert to cosine similarity
            }
            if prod_id in self.metadata:
                result.update(self.metadata[prod_id])
            results.append(result)
        
        return results
    
    def save(self, index_path: str, metadata_path: str) -> None:
        """
        Save index and metadata to disk.
        
        Args:
            index_path: Path to save FAISS index
            metadata_path: Path to save metadata JSON
        """
        try:
            os.makedirs(os.path.dirname(index_path), exist_ok=True)
            os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
            
            faiss.write_index(self.index, index_path)
            
            # Save metadata and product IDs
            metadata = {
                "product_ids": self.product_ids,
                "metadata": {str(k): v for k, v in self.metadata.items()}
            }
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Saved index to {index_path}")
            logger.info(f"Saved metadata to {metadata_path}")
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            raise
    
    def load(self, index_path: str, metadata_path: str) -> None:
        """
        Load index and metadata from disk.
        
        Args:
            index_path: Path to FAISS index
            metadata_path: Path to metadata JSON
        """
        try:
            self.index = faiss.read_index(index_path)
            
            with open(metadata_path, "r") as f:
                data = json.load(f)
            
            self.product_ids = data["product_ids"]
            self.metadata = {int(k): v for k, v in data["metadata"].items()}
            
            logger.info(f"Loaded index from {index_path}")
            logger.info(f"Loaded {len(self.product_ids)} products")
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            raise
    
    def get_size(self) -> int:
        """Get number of products in index."""
        return len(self.product_ids)
    
    def get_metadata(self, product_id: int) -> Optional[Dict]:
        """Get metadata for a product."""
        return self.metadata.get(product_id)
