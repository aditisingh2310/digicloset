import numpy as np
import logging

logger = logging.getLogger(__name__)

class RankingService:
    def __init__(self, vector_store):
        self.vector_store = vector_store
        # In-memory user profiles: mapping of user_id -> profile_vector (numpy array)
        self.user_profiles = {}
        
    def record_interaction(self, user_id: str, item_id: str, weight: float = 0.5) -> bool:
        """
        Updates the user's personalization profile based on interaction with an item.
        Weight dictates how much the profile shifts toward this item (0.0 to 1.0).
        """
        item_vector = self.vector_store.get_embedding(item_id)
        if item_vector is None:
            logger.warning(f"Item {item_id} not found in VectorStore. Cannot update profile.")
            return False
            
        vector_np = np.array(item_vector, dtype=np.float32)
        
        if user_id not in self.user_profiles:
            # First interaction, profile strictly becomes this vector
            self.user_profiles[user_id] = vector_np
        else:
            # Exponential Moving Average shift
            current_profile = self.user_profiles[user_id]
            new_profile = (1.0 - weight) * current_profile + weight * vector_np
            # Re-normalize to maintain cosine similarity semantics
            norm = np.linalg.norm(new_profile)
            if norm > 0:
                new_profile = new_profile / norm
            self.user_profiles[user_id] = new_profile
            
        logger.info(f"Updated user {user_id} profile with item {item_id} (weight={weight})")
        return True
        
    def rank_candidates(self, user_id: str, candidates: list[dict], alpha: float = 0.7) -> list[dict]:
        """
        Re-ranks a list of candidates combining their original FAISS score 
        with their personalization score against the user's profile.
        candidates: [{"id": "item1", "score": 0.95}, ...]
        alpha: Weight of the original score (0.0 to 1.0). (1 - alpha) is given to personalization.
        """
        if user_id not in self.user_profiles or not candidates:
            return candidates # No personalization available
            
        user_vector = self.user_profiles[user_id]
        ranked_candidates = []
        
        for candidate in candidates:
            item_id = candidate["id"]
            original_score = candidate["score"]
            
            # Fetch item vector from FAISS to compare with user profile
            item_vector = self.vector_store.get_embedding(item_id)
            if item_vector is None:
                ranked_candidates.append({
                    "id": item_id,
                    "score": original_score,
                    "original_score": original_score,
                    "personalization_score": None
                })
                continue
                
            item_vector_np = np.array(item_vector, dtype=np.float32)
            
            # Calculate cosine similarity between user profile and item
            personalization_score = float(np.dot(user_vector, item_vector_np))
            
            # Combine scores
            final_score = (alpha * original_score) + ((1.0 - alpha) * personalization_score)
            
            ranked_candidates.append({
                "id": item_id,
                "score": final_score,
                "original_score": original_score,
                "personalization_score": personalization_score
            })            
        # Sort by final score descending
        return sorted(ranked_candidates, key=lambda x: x["score"], reverse=True)
