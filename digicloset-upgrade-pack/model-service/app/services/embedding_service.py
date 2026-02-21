import torch
import open_clip
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading OpenCLIP model (ViT-B-32) on {self.device}...")
        
        # Load the ViT-B-32 model and its corresponding transforms
        model, _, preprocess = open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k')
        self.model = model.to(self.device)
        self.model.eval()  # Set to evaluation mode
        self.preprocess = preprocess
        logger.info("OpenCLIP model loaded successfully.")

    def generate_embedding(self, image_bytes: bytes) -> list[float]:
        """
        Takes raw image bytes, runs it through the OpenCLIP vision encoder,
        and returns a normalized 512-dimensional float list.
        """
        try:
            # Load and preprocess image
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)

            # Generate and normalize embedding
            with torch.no_grad():
                image_features = self.model.encode_image(image_input)
                image_features /= image_features.norm(dim=-1, keepdim=True)
                
            # Move back to CPU, convert to list
            embedding_list = image_features.cpu().numpy()[0].tolist()
            return embedding_list
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise e

    def generate_text_embedding(self, text: str) -> list[float]:
        """
        Takes a string of text, runs it through the OpenCLIP text encoder,
        and returns a normalized 512-dimensional float list.
        """
        try:
            text_input = open_clip.tokenize([text]).to(self.device)
            
            with torch.no_grad():
                text_features = self.model.encode_text(text_input)
                text_features /= text_features.norm(dim=-1, keepdim=True)
                
            embedding_list = text_features.cpu().numpy()[0].tolist()
            return embedding_list
            
        except Exception as e:
            logger.error(f"Failed to generate text embedding: {str(e)}")
            raise e
