"""Image validation service"""

import logging
from typing import Tuple, Optional
import io
import requests
from PIL import Image

logger = logging.getLogger(__name__)


class ImageValidator:
    """Validates images before processing"""
    
    # Minimum resolution
    MIN_WIDTH = 512
    MIN_HEIGHT = 512
    
    # Maximum resolution
    MAX_WIDTH = 4096
    MAX_HEIGHT = 4096
    
    # Maximum file size (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    # Allowed MIME types
    ALLOWED_MIMES = {'image/jpeg', 'image/png', 'image/webp'}
    
    # Allowed extensions
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
    
    @staticmethod
    def validate_image_url(image_url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate image by URL
        
        Args:
            image_url: URL of image to validate
            
        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])
        """
        try:
            # Download image
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            
            # Check file size
            if len(response.content) > ImageValidator.MAX_FILE_SIZE:
                return False, f"Image too large (max {ImageValidator.MAX_FILE_SIZE / 1024 / 1024:.0f}MB)"
            
            # Check MIME type
            content_type = response.headers.get('content-type', '')
            if not any(mime in content_type for mime in ImageValidator.ALLOWED_MIMES):
                return False, f"Invalid image format. Allowed: JPEG, PNG, WebP"
            
            # Validate image
            image_data = io.BytesIO(response.content)
            return ImageValidator.validate_image_file(image_data)
            
        except requests.RequestException as e:
            return False, f"Failed to download image: {str(e)}"
        except Exception as e:
            return False, f"Image validation failed: {str(e)}"
    
    @staticmethod
    def validate_image_file(file_data: io.BytesIO) -> Tuple[bool, Optional[str]]:
        """
        Validate image file data
        
        Args:
            file_data: Image file bytes
            
        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])
        """
        try:
            # Open image
            image = Image.open(file_data)
            
            # Check format
            if image.format and image.format.lower() not in ['jpeg', 'png', 'webp']:
                return False, f"Invalid image format: {image.format}"
            
            # Check dimensions
            width, height = image.size
            
            if width < ImageValidator.MIN_WIDTH or height < ImageValidator.MIN_HEIGHT:
                return False, f"Image too small (min {ImageValidator.MIN_WIDTH}x{ImageValidator.MIN_HEIGHT}px, got {width}x{height}px)"
            
            if width > ImageValidator.MAX_WIDTH or height > ImageValidator.MAX_HEIGHT:
                return False, f"Image too large (max {ImageValidator.MAX_WIDTH}x{ImageValidator.MAX_HEIGHT}px, got {width}x{height}px)"
            
            logger.info(f"Image validation successful: {width}x{height} {image.format}")
            return True, None
            
        except Exception as e:
            return False, f"Failed to read image: {str(e)}"
    
    @staticmethod
    def validate_batch(image_urls: list) -> dict:
        """
        Validate multiple images
        
        Args:
            image_urls: List of image URLs
            
        Returns:
            Dict with validation results
        """
        results = {
            "total": len(image_urls),
            "valid": 0,
            "invalid": 0,
            "errors": {}
        }
        
        for url in image_urls:
            is_valid, error = ImageValidator.validate_image_url(url)
            
            if is_valid:
                results["valid"] += 1
            else:
                results["invalid"] += 1
                results["errors"][url] = error
        
        return results


# Global validator instance
_validator = None


def get_image_validator() -> ImageValidator:
    """Get image validator instance"""
    global _validator
    if _validator is None:
        _validator = ImageValidator()
    return _validator
