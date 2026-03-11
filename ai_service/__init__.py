"""
Shopify Fashion AI Recommendation Service.

A production-ready visual and multimodal recommendation engine using CLIP embeddings
and FAISS vector search for Shopify fashion catalogs.
"""

__version__ = "1.0.0"
__author__ = "Shopify AI Team"

from .embeddings import CLIPEmbedder
from .vector_db import ProductVectorIndex
from .recommendation import Recommender

__all__ = [
    "CLIPEmbedder",
    "ProductVectorIndex",
    "Recommender",
]
