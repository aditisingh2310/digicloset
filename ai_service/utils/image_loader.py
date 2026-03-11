"""Image loading and processing utilities."""

import logging
from io import BytesIO
from typing import Optional
import requests
from PIL import Image

logger = logging.getLogger(__name__)

# Image size for processing
DEFAULT_IMAGE_SIZE = (224, 224)
REQUEST_TIMEOUT = 10  # seconds


def download_image(
    url: str,
    timeout: int = REQUEST_TIMEOUT,
    retries: int = 3
) -> Optional[Image.Image]:
    """
    Download and open an image from URL.
    
    Args:
        url: Image URL
        timeout: Request timeout in seconds
        retries: Number of retry attempts
        
    Returns:
        PIL Image object or None if download fails
    """
    if not url:
        logger.warning("Empty URL provided")
        return None
    
    for attempt in range(retries):
        try:
            response = requests.get(
                url,
                timeout=timeout,
                allow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                }
            )
            response.raise_for_status()
            
            image = Image.open(BytesIO(response.content))
            
            # Convert to RGB if necessary
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            logger.debug(f"Downloaded image from {url}")
            return image
        
        except requests.RequestException as e:
            if attempt < retries - 1:
                logger.warning(f"Download attempt {attempt + 1} failed: {e}, retrying...")
            else:
                logger.error(f"Failed to download image from {url}: {e}")
                return None
        except Exception as e:
            logger.error(f"Failed to process downloaded image: {e}")
            return None
    
    return None


class ImageLoader:
    """Utility class for loading and preprocessing images."""
    
    def __init__(
        self,
        target_size: tuple = DEFAULT_IMAGE_SIZE,
        maintain_aspect: bool = True
    ):
        """
        Initialize image loader.
        
        Args:
            target_size: Target size for resizing
            maintain_aspect: Whether to maintain aspect ratio when resizing
        """
        self.target_size = target_size
        self.maintain_aspect = maintain_aspect
    
    def load_from_url(self, url: str) -> Optional[Image.Image]:
        """Load image from URL."""
        return download_image(url)
    
    def load_from_path(self, path: str) -> Optional[Image.Image]:
        """
        Load image from file path.
        
        Args:
            path: File path
            
        Returns:
            PIL Image or None if fails
        """
        try:
            image = Image.open(path)
            if image.mode != "RGB":
                image = image.convert("RGB")
            return image
        except Exception as e:
            logger.error(f"Failed to load image from {path}: {e}")
            return None
    
    def preprocess(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for embedding.
        
        Args:
            image: PIL Image
            
        Returns:
            Preprocessed PIL Image
        """
        if self.maintain_aspect:
            # Resize with aspect ratio maintained (add padding)
            image.thumbnail(self.target_size, Image.Resampling.LANCZOS)
            
            # Add padding if needed
            new_image = Image.new(
                "RGB",
                self.target_size,
                color=(255, 255, 255)
            )
            offset = (
                (self.target_size[0] - image.width) // 2,
                (self.target_size[1] - image.height) // 2
            )
            new_image.paste(image, offset)
            return new_image
        else:
            # Simple resize ignoring aspect ratio
            return image.resize(self.target_size, Image.Resampling.LANCZOS)
