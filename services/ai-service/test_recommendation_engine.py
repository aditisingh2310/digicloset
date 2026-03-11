"""
Integration tests for the recommendation engine.

Tests indexing, similarity search, style matching, and outfit generation.
"""

import pytest
import json
import numpy as np
from typing import Dict, List

# Import the components (adjust imports based on your structure)
try:
    from ai_service.embeddings import CLIPEmbedder
    from ai_service.vector_db import ProductVectorIndex
    from ai_service.recommendation import Recommender
    from ai_service.indexing import CatalogIndexer
except ImportError:
    pytest.skip("AI service modules not available", allow_module_level=True)


class TestCLIPEmbedder:
    """Tests for CLIP embedder."""
    
    @pytest.fixture
    def embedder(self):
        """Initialize embedder."""
        return CLIPEmbedder(model_name="openai/clip-vit-base-patch32")
    
    def test_embedder_initialization(self, embedder):
        """Test embedder initialization."""
        assert embedder is not None
        assert embedder.embedding_dim == 512
        assert embedder.device in ["cpu", "cuda", "cuda:0"]
    
    def test_text_embedding(self, embedder):
        """Test text embedding generation."""
        text = "A beautiful white cotton t-shirt"
        embedding = embedder.embed_text(text)
        
        assert embedding is not None
        assert len(embedding) == 512
        assert embedding.dtype == np.float32
        # Check normalization
        norm = np.linalg.norm(embedding)
        assert abs(norm - 1.0) < 0.01
    
    def test_text_embedding_empty(self, embedder):
        """Test text embedding with empty string."""
        embedding = embedder.embed_text("")
        assert embedding is not None
        assert len(embedding) == 512


class TestProductVectorIndex:
    """Tests for product vector index."""
    
    @pytest.fixture
    def index(self):
        """Initialize vector index."""
        return ProductVectorIndex(embedding_dim=512)
    
    def test_index_initialization(self, index):
        """Test index initialization."""
        assert index is not None
        assert index.embedding_dim == 512
        assert index.get_size() == 0
    
    def test_add_single_product(self, index):
        """Test adding a single product."""
        embedding = np.random.rand(512).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)
        
        metadata = {
            "title": "Test Product",
            "category": "shirt",
            "tags": ["test"]
        }
        
        index.add_product(1, embedding, metadata)
        assert index.get_size() == 1
        assert index.get_metadata(1) is not None
    
    def test_batch_add_products(self, index):
        """Test batch adding products."""
        products = []
        for i in range(5):
            embedding = np.random.rand(512).astype(np.float32)
            embedding = embedding / np.linalg.norm(embedding)
            metadata = {"title": f"Product {i}", "category": "shirt"}
            products.append((i, embedding, metadata))
        
        index.batch_add(products)
        assert index.get_size() == 5
    
    def test_search(self, index):
        """Test similarity search."""
        # Add some products
        for i in range(3):
            embedding = np.random.rand(512).astype(np.float32)
            embedding = embedding / np.linalg.norm(embedding)
            index.add_product(i, embedding)
        
        # Search with a query embedding
        query = np.random.rand(512).astype(np.float32)
        query = query / np.linalg.norm(query)
        
        product_ids, distances = index.search(query, k=2)
        assert len(product_ids) == 2
        assert len(distances) == 2
        assert all(pid in [0, 1, 2] for pid in product_ids)
    
    def test_search_with_metadata(self, index):
        """Test search with metadata."""
        for i in range(3):
            embedding = np.random.rand(512).astype(np.float32)
            embedding = embedding / np.linalg.norm(embedding)
            metadata = {"title": f"Product {i}", "category": "shirt"}
            index.add_product(i, embedding, metadata)
        
        query = np.random.rand(512).astype(np.float32)
        query = query / np.linalg.norm(query)
        
        results = index.search_with_metadata(query, k=2)
        assert len(results) == 2
        assert "product_id" in results[0]
        assert "similarity" in results[0]
        assert "title" in results[0]


class TestRecommender:
    """Tests for recommendation engine."""
    
    @pytest.fixture
    def recommender_setup(self):
        """Setup recommender with sample data."""
        index = ProductVectorIndex(embedding_dim=512)
        
        # Add sample products
        products = [
            ("white-tshirt", "shirt", ["casual", "white"]),
            ("blue-jeans", "pants", ["casual", "blue"]),
            ("black-jacket", "jacket", ["formal", "black"]),
            ("white-sneakers", "shoes", ["casual", "white"]),
            ("red-heels", "heels", ["formal", "red"]),
        ]
        
        for product_id, (name, category, tags) in enumerate(products, 1):
            embedding = np.random.rand(512).astype(np.float32)
            embedding = embedding / np.linalg.norm(embedding)
            metadata = {
                "title": name.replace("-", " ").title(),
                "category": category,
                "tags": tags
            }
            index.add_product(product_id, embedding, metadata)
        
        recommender = Recommender(index)
        return recommender, index
    
    def test_recommender_initialization(self, recommender_setup):
        """Test recommender initialization."""
        recommender, _ = recommender_setup
        assert recommender is not None
        assert recommender.color_weight == 0.2
        assert recommender.similarity_threshold == 0.3
    
    def test_recommend_similar_products(self, recommender_setup):
        """Test similar product recommendations."""
        recommender, index = recommender_setup
        
        # Should return empty or some recommendations
        recommendations = recommender.recommend_similar_products(
            product_id=1,
            top_k=3
        )
        assert isinstance(recommendations, list)
    
    def test_recommend_style_matches(self, recommender_setup):
        """Test style matching recommendations."""
        recommender, index = recommender_setup
        
        recommendations = recommender.recommend_style_matches(
            product_id=1,
            top_k=3
        )
        assert isinstance(recommendations, list)
    
    def test_recommend_complete_outfit(self, recommender_setup):
        """Test outfit generation."""
        recommender, index = recommender_setup
        
        outfit = recommender.recommend_complete_outfit(
            product_id=1,
            max_items=4
        )
        assert isinstance(outfit, dict)
        assert "base_product_id" in outfit
        assert "outfit_items" in outfit


class TestCatalogIndexer:
    """Tests for catalog indexing."""
    
    @pytest.fixture
    def indexer_setup(self):
        """Setup indexer with embedder and vector index."""
        embedder = CLIPEmbedder(model_name="openai/clip-vit-base-patch32")
        index = ProductVectorIndex(embedding_dim=512)
        from ai_service.indexing import CatalogIndexer
        indexer = CatalogIndexer(embedder, index)
        return indexer, index
    
    def test_indexer_initialization(self, indexer_setup):
        """Test indexer initialization."""
        indexer, _ = indexer_setup
        assert indexer is not None
        assert indexer.embedder is not None
        assert indexer.vector_index is not None


class TestIntegration:
    """Integration tests for complete workflow."""
    
    def test_full_workflow(self):
        """Test complete workflow: init -> index -> recommend."""
        # Initialize
        embedder = CLIPEmbedder(model_name="openai/clip-vit-base-patch32")
        index = ProductVectorIndex(embedding_dim=512)
        recommender = Recommender(index)
        
        # Add products
        sample_products = [
            {"id": 1, "title": "White T-Shirt", "category": "shirt"},
            {"id": 2, "title": "Blue Jeans", "category": "pants"},
        ]
        
        for product in sample_products:
            # Generate embedding from text
            embedding = embedder.embed_text(product["title"])
            metadata = {
                "title": product["title"],
                "category": product["category"]
            }
            index.add_product(product["id"], embedding, metadata)
        
        # Verify indexing
        assert index.get_size() == 2
        
        # Test search
        query_embedding = embedder.embed_text("White T-Shirt")
        results = index.search_with_metadata(query_embedding, k=1)
        assert len(results) > 0
        
        print("✓ Full workflow test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
