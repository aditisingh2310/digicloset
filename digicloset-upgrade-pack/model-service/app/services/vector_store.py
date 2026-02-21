import faiss
import numpy as np
import os
import pickle
import logging

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, dimension=512, store_dir="/tmp/digicloset_vectors"):
        self.dimension = dimension
        self.store_dir = store_dir
        self.index_path = os.path.join(store_dir, "faiss_index.bin")
        self.mapping_path = os.path.join(store_dir, "id_mapping.pkl")
        
        # FAISS index (IndexFlatIP computes precise Cosine Similarity if vectors are normalized)
        self.index = faiss.IndexFlatIP(self.dimension)
        
        # Maps FAISS integer IDs (0, 1, 2) to String IDs ('dress_123', 'shirt_456')
        self.id_map = {}
        self.next_id = 0

        # Create dir if not exists
        if not os.path.exists(self.store_dir):
            os.makedirs(self.store_dir)
            
        self.load()

    def add_item(self, item_id: str, embedding: list[float]):
        """
        Adds a single embedding to the FAISS index and stores the String ID.
        Expects a normalized float list.
        """
        try:
            # Convert python list to numpy float32 array
            vector = np.array([embedding], dtype=np.float32)
            
            # Add to FAISS
            self.index.add(vector)
            
            # Map the integer ID FAISS assigned to our real String ID
            self.id_map[self.next_id] = item_id
            self.next_id += 1
            
            # Save state
            self.save()
            logger.info(f"Added item {item_id} to Vector DB.")
        except Exception as e:
            logger.error(f"Failed to add {item_id} to Vector DB: {str(e)}")
            raise e

    def search_similar(self, query_embedding: list[float], top_k: int = 5) -> list[dict]:
        """
        Queries the FAISS index for the closest top_k neighbors.
        Returns a list of dictionaries with matching item IDs and their cosine similarity score.
        """
        if self.index.ntotal == 0:
            return []

        try:
            vector = np.array([query_embedding], dtype=np.float32)
            
            # Perform search
            scores, indices = self.index.search(vector, top_k)
            
            results = []
            # FAISS returns a 2D array, we used 1 query vector so we read the 0th row
            for score, idx in zip(scores[0], indices[0]):
                if idx != -1 and idx in self.id_map:
                    results.append({
                        "id": self.id_map[idx],
                        "score": float(score)
                    })
            return results
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise e

    def get_embedding(self, item_id: str) -> list[float]:
        """Retrieve the original embedding vector for a given string ID."""
        internal_id = None
        for k, v in self.id_map.items():
            if v == item_id:
                internal_id = k
                break
        
        if internal_id is None:
            return None
            
        try:
            vector = self.index.reconstruct(internal_id)
            return vector.tolist()
        except Exception as e:
            logger.error(f"Failed to reconstruct vector for {item_id}: {str(e)}")
            return None

    def save(self):
        """Persist FAISS index and string mappings to disk."""
        try:
            faiss.write_index(self.index, self.index_path)
            with open(self.mapping_path, "wb") as f:
                pickle.dump((self.id_map, self.next_id), f)
        except Exception as e:
            logger.error(f"Failed to save Vector DB: {str(e)}")

    def load(self):
        """Restore FAISS index and string mappings from disk."""
        if os.path.exists(self.index_path) and os.path.exists(self.mapping_path):
            try:
                self.index = faiss.read_index(self.index_path)
                with open(self.mapping_path, "rb") as f:
                    self.id_map, self.next_id = pickle.load(f)
                logger.info(f"Loaded {self.index.ntotal} items from Vector DB.")
            except Exception as e:
                logger.error(f"Failed to load Vector DB: {str(e)}")
