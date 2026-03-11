"""CLIP-based multimodal embedder for product images and text."""

import logging
from typing import Optional, Tuple
import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

logger = logging.getLogger(__name__)


class CLIPEmbedder:
    """
    CLIP embedder for generating multimodal embeddings from images and text.
    
    Uses OpenAI's CLIP model to create normalized embeddings for:
    - Product images
    - Product titles and descriptions
    - Combined multimodal embeddings
    """

    def __init__(
        self,
        model_name: str = "openai/clip-vit-base-patch32",
        device: Optional[str] = None,
        embedding_dim: int = 512,
    ):
        """
        Initialize the CLIP embedder.
        
        Args:
            model_name: HuggingFace model identifier
            device: Device to use ('cuda', 'cpu'). Auto-detects if None
            embedding_dim: Expected dimension of embeddings (for validation)
        """
        self.model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.embedding_dim = embedding_dim
        
        logger.info(f"Loading CLIP model '{model_name}' on {self.device}")
        try:
            self.model = CLIPModel.from_pretrained(model_name).to(self.device)
            self.processor = CLIPProcessor.from_pretrained(model_name)
            self.model.eval()
            logger.info(f"CLIP model loaded successfully. Device: {self.device}")
        except Exception as e:
            logger.error(f"Failed to load CLIP model: {e}")
            raise
    
    def embed_image(self, image: Image.Image) -> np.ndarray:
        """
        Generate embedding for a product image.
        
        Args:
            image: PIL Image object
            
        Returns:
            Normalized embedding vector (float32)
            
        Raises:
            ValueError: If image is invalid or processing fails
        """
        try:
            if not isinstance(image, Image.Image):
                raise ValueError(f"Expected PIL Image, got {type(image)}")
            
            # Preprocess image
            inputs = self.processor(
                images=image, 
                return_tensors="pt",
                padding=True
            ).to(self.device)
            
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
            
            # Normalize embedding
            embedding = image_features[0].cpu().numpy().astype(np.float32)
            embedding = embedding / np.linalg.norm(embedding)
            
            return embedding
        except Exception as e:
            logger.error(f"Failed to embed image: {e}")
            raise ValueError(f"Image embedding failed: {e}")
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for text (title or description).
        
        Args:
            text: Text to embed
            
        Returns:
            Normalized embedding vector (float32)
            
        Raises:
            ValueError: If text is invalid or processing fails
        """
        try:
            if not text or not isinstance(text, str):
                raise ValueError(f"Expected non-empty string, got {text}")
            
            # Preprocess text
            inputs = self.processor(
                text=text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=77
            ).to(self.device)
            
            with torch.no_grad():
                text_features = self.model.get_text_features(**inputs)
            
            # Normalize embedding
            embedding = text_features[0].cpu().numpy().astype(np.float32)
            embedding = embedding / np.linalg.norm(embedding)
            
            return embedding
        except Exception as e:
            logger.error(f"Failed to embed text: {e}")
            raise ValueError(f"Text embedding failed: {e}")
    
    def embed_product(
        self,
        image: Optional[Image.Image] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        image_weight: float = 0.6,
        title_weight: float = 0.2,
        description_weight: float = 0.2,
    ) -> Tuple[np.ndarray, dict]:
        """
        Generate combined multimodal embedding for a product.
        
        Creates a weighted combination of image, title, and description embeddings.
        
        Args:
            image: PIL Image object (optional)
            title: Product title (optional)
            description: Product description (optional)
            image_weight: Weight for image embedding
            title_weight: Weight for title embedding
            description_weight: Weight for description embedding
            
        Returns:
            Tuple of (combined_embedding, embedding_sources) where embedding_sources
            tracks which modalities were used
            
        Raises:
            ValueError: If no input provided or all processing fails
        """
        if not any([image, title, description]):
            raise ValueError("At least one of image, title, or description must be provided")
        
        embeddings = []
        weights = []
        sources = {
            "image": False,
            "title": False,
            "description": False
        }
        
        # Embed image if provided
        if image is not None:
            try:
                image_emb = self.embed_image(image)
                embeddings.append(image_emb)
                weights.append(image_weight)
                sources["image"] = True
            except Exception as e:
                logger.warning(f"Image embedding failed: {e}, continuing with text")
        
        # Embed title if provided
        if title is not None:
            try:
                title_emb = self.embed_text(title)
                embeddings.append(title_emb)
                weights.append(title_weight)
                sources["title"] = True
            except Exception as e:
                logger.warning(f"Title embedding failed: {e}, continuing")
        
        # Embed description if provided
        if description is not None:
            try:
                desc_emb = self.embed_text(description)
                embeddings.append(desc_emb)
                weights.append(description_weight)
                sources["description"] = True
            except Exception as e:
                logger.warning(f"Description embedding failed: {e}, continuing")
        
        if not embeddings:
            raise ValueError("Failed to generate any embeddings")
        
        # Normalize weights
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]
        
        # Combine embeddings
        combined = np.zeros(embeddings[0].shape, dtype=np.float32)
        for emb, weight in zip(embeddings, weights):
            combined += emb * weight
        
        # Final normalization
        combined = combined / np.linalg.norm(combined)
        
        return combined, sources
