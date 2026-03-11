"""Fashion recommendation engine with outfit compatibility scoring."""

import logging
from typing import Dict, List, Optional, Tuple
import numpy as np

from ..vector_db import ProductVectorIndex
from ..utils import get_dominant_colors, color_similarity

logger = logging.getLogger(__name__)


# Fashion compatibility rules mapping
COMPATIBILITY_RULES = {
    "shirt": ["pants", "jacket", "shoes", "belt", "watch"],
    "pants": ["shirt", "jacket", "shoes", "belt", "watch"],
    "dress": ["heels", "flats", "shoes", "bag", "jacket"],
    "jacket": ["shirt", "pants", "dress", "shoes", "watch"],
    "shoes": ["shirt", "pants", "dress", "jacket", "socks"],
    "heels": ["dress", "pants", "skirt", "bag"],
    "flats": ["dress", "pants", "skirt", "shirt"],
    "bag": ["dress", "shoes", "accessories"],
    "skirt": ["shirt", "heels", "flats", "shoes"],
    "sweater": ["pants", "skirt", "shoes", "jacket"],
    "t-shirt": ["pants", "jacket", "shorts", "shoes"],
    "shorts": ["t-shirt", "shirt", "shoes", "jacket"],
    "belt": ["pants", "shorts", "dress"],
    "accessories": ["any"],
    "watch": ["any"],
    "socks": ["shoes", "pants"]
}


class Recommender:
    """
    Fashion recommendation engine using multimodal embeddings.
    
    Provides three recommendation types:
    1. Visual similarity: Products with similar embeddings
    2. Style match: Different categories but compatible style
    3. Complete outfit: Recommendations for outfit completion
    """
    
    def __init__(
        self,
        vector_index: ProductVectorIndex,
        color_weight: float = 0.2,
        similarity_threshold: float = 0.3
    ):
        """
        Initialize recommender.
        
        Args:
            vector_index: ProductVectorIndex instance
            color_weight: Weight for color similarity in scoring
            similarity_threshold: Minimum similarity for recommendations
        """
        self.vector_index = vector_index
        self.color_weight = color_weight
        self.similarity_threshold = similarity_threshold
    
    def recommend_similar_products(
        self,
        product_id: int,
        top_k: int = 10,
        exclude_category: bool = False
    ) -> List[Dict]:
        """
        Find visually similar products.
        
        Args:
            product_id: Query product ID
            top_k: Number of recommendations
            exclude_category: If True, exclude same category
            
        Returns:
            List of recommended products with scores
        """
        try:
            product_metadata = self.vector_index.get_metadata(product_id)
            if not product_metadata:
                logger.warning(f"Product {product_id} not found in index")
                return []
            
            # Get embedding by searching for the product
            # Since we don't store embeddings separately, we need to find it
            # For now, we'll search with a dummy and filter
            logger.info(f"Finding similar products to {product_id}")
            
            source_category = product_metadata.get("category", "")
            
            # Get more candidates to filter
            candidates = self.vector_index.search_with_metadata(
                np.zeros(512, dtype=np.float32),  # Placeholder
                k=min(100, self.vector_index.get_size())
            )
            
            # Filter and score
            recommendations = []
            for item in candidates:
                if item["product_id"] == product_id:
                    continue
                
                if exclude_category:
                    item_category = item.get("category", "")
                    if item_category == source_category:
                        continue
                
                if item["similarity"] >= self.similarity_threshold:
                    recommendations.append(item)
            
            return recommendations[:top_k]
        
        except Exception as e:
            logger.error(f"Error in recommend_similar_products: {e}")
            return []
    
    def recommend_style_matches(
        self,
        product_id: int,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Find style-compatible products in different categories.
        
        Finds products that complement the given item's style.
        
        Args:
            product_id: Query product ID
            top_k: Number of recommendations
            
        Returns:
            List of style-matched products
        """
        try:
            product_metadata = self.vector_index.get_metadata(product_id)
            if not product_metadata:
                return []
            
            source_category = product_metadata.get("category", "").lower()
            source_colors = product_metadata.get("colors", [])
            
            # Get compatible categories
            compatible_categories = COMPATIBILITY_RULES.get(
                source_category, ["any"]
            )
            
            logger.info(
                f"Finding style matches for {product_id} "
                f"(category: {source_category})"
            )
            
            # Get all products for scoring
            all_candidates = self.vector_index.search_with_metadata(
                np.zeros(512, dtype=np.float32),
                k=self.vector_index.get_size()
            )
            
            scored_recommendations = []
            
            for item in all_candidates:
                if item["product_id"] == product_id:
                    continue
                
                item_category = item.get("category", "").lower()
                
                # Check category compatibility
                if (compatible_categories != ["any"] and 
                    item_category not in compatible_categories):
                    continue
                
                # Score based on embedding similarity and color compatibility
                base_score = item.get("similarity", 0.5)
                
                # Add color similarity bonus
                item_colors = item.get("colors", [])
                if source_colors and item_colors:
                    color_match = max(
                        color_similarity(c1, c2)
                        for c1 in source_colors[:2]
                        for c2 in item_colors[:2]
                    )
                    base_score += color_match * self.color_weight
                
                item["compatibility_score"] = min(base_score, 1.0)
                scored_recommendations.append(item)
            
            # Sort by compatibility score
            scored_recommendations.sort(
                key=lambda x: x["compatibility_score"],
                reverse=True
            )
            
            return scored_recommendations[:top_k]
        
        except Exception as e:
            logger.error(f"Error in recommend_style_matches: {e}")
            return []
    
    def recommend_complete_outfit(
        self,
        product_id: int,
        max_items: int = 4,
        include_scores: bool = True
    ) -> Dict:
        """
        Generate complete outfit recommendations.
        
        Builds a coordinated outfit with compatible items based on fashion rules.
        
        Args:
            product_id: Base product ID
            max_items: Maximum items to include in outfit
            include_scores: Include compatibility scores in response
            
        Returns:
            Dict with outfit items and details
        """
        try:
            product_metadata = self.vector_index.get_metadata(product_id)
            if not product_metadata:
                return {"error": "Product not found"}
            
            base_category = product_metadata.get("category", "").lower()
            base_colors = product_metadata.get("colors", [])
            
            logger.info(f"Building outfit around product {product_id}")
            
            # Get compatible categories
            compatible = COMPATIBILITY_RULES.get(base_category, ["any"])
            
            outfit_items = [
                {
                    "product_id": product_id,
                    "role": "base",
                    "category": base_category,
                    **product_metadata
                }
            ]
            
            # Get candidates
            all_products = self.vector_index.search_with_metadata(
                np.zeros(512, dtype=np.float32),
                k=self.vector_index.get_size()
            )
            
            # Score and select items for outfit
            scored_items = []
            
            for item in all_products:
                if item["product_id"] == product_id:
                    continue
                
                item_category = item.get("category", "").lower()
                
                # Check compatibility
                if (compatible != ["any"] and 
                    item_category not in compatible):
                    continue
                
                # Calculate outfit score
                outfit_score = self._calculate_outfit_score(
                    product_metadata,
                    item,
                    base_colors
                )
                
                if outfit_score >= self.similarity_threshold:
                    item["outfit_score"] = outfit_score
                    item["role"] = self._determine_role(item_category)
                    scored_items.append(item)
            
            # Select diverse items (different categories)
            selected_categories = {base_category}
            for item in sorted(scored_items, key=lambda x: x["outfit_score"], reverse=True):
                if len(outfit_items) >= max_items:
                    break
                
                item_cat = item.get("category", "").lower()
                if item_cat not in selected_categories:
                    outfit_items.append(item)
                    selected_categories.add(item_cat)
            
            # Prepare response
            response = {
                "base_product_id": product_id,
                "base_category": base_category,
                "outfit_items": outfit_items if include_scores else [
                    {k: v for k, v in item.items() if k != "outfit_score"}
                    for item in outfit_items
                ],
                "total_items": len(outfit_items),
                "outfit_score": np.mean([
                    item.get("outfit_score", 0.7) for item in outfit_items[1:]
                ]) if len(outfit_items) > 1 else 0.5
            }
            
            return response
        
        except Exception as e:
            logger.error(f"Error in recommend_complete_outfit: {e}")
            return {"error": str(e)}
    
    def _calculate_outfit_score(
        self,
        base_product: Dict,
        candidate: Dict,
        base_colors: List[Tuple[int, int, int]]
    ) -> float:
        """
        Calculate compatibility score for outfit combination.
        
        Args:
            base_product: Base product metadata
            candidate: Candidate product metadata
            base_colors: Base product colors
            
        Returns:
            Compatibility score (0-1)
        """
        # Embedding similarity
        embedding_score = candidate.get("similarity", 0.5)
        
        # Color complementarity
        candidate_colors = candidate.get("colors", [])
        color_score = 0.5  # Default neutral score
        
        if base_colors and candidate_colors:
            color_score = np.mean([
                color_similarity(c1, c2)
                for c1 in base_colors[:2]
                for c2 in candidate_colors[:2]
            ])
        
        # Category compatibility bonus
        base_cat = base_product.get("category", "").lower()
        cand_cat = candidate.get("category", "").lower()
        category_bonus = 0.1 if cand_cat in COMPATIBILITY_RULES.get(
            base_cat, []
        ) else 0.0
        
        # Weighted combination
        outfit_score = (
            embedding_score * 0.4 +
            color_score * 0.4 +
            category_bonus
        )
        
        return min(outfit_score, 1.0)
    
    def _determine_role(self, category: str) -> str:
        """Determine the role/purpose of item in outfit."""
        category = category.lower()
        
        roles = {
            "shoes": "footwear",
            "heels": "footwear",
            "flats": "footwear",
            "bag": "accessory",
            "watch": "accessory",
            "belt": "accessory",
            "socks": "accessory",
            "jacket": "outerwear",
            "sweater": "outerwear",
            "dress": "dress",
            "pants": "bottoms",
            "shorts": "bottoms",
            "skirt": "bottoms",
            "shirt": "tops",
            "t-shirt": "tops"
        }
        
        return roles.get(category, "accessory")
