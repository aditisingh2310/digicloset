import io
import logging
from PIL import Image
import rembg

logger = logging.getLogger(__name__)

class BackgroundRemovalService:
    def __init__(self):
        self.session = None

    def _get_session(self):
        if self.session is None:
            try:
                logger.info("Initializing rembg (U-2-Net) session (this may trigger a model download on first run)...")
                self.session = rembg.new_session()
                logger.info("Initialized rembg session successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize rembg session: {str(e)}")
                raise RuntimeError(f"rembg session failed to initialize: {str(e)}")
        return self.session

    def _hex_to_rgb(self, hex_color: str):
        """Convert a hex color string like '#FFFFFF' to an RGB tuple."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return (255, 255, 255) # Default to white

    def remove_background(self, image_bytes: bytes, bg_color: str = None) -> bytes:
        """
        Removes the background from the provided image bytes.
        If bg_color is provided (e.g. '#FFFFFF'), it composites the foreground 
        onto a solid background of that color and returns a JPEG.
        Otherwise, it returns a transparent PNG.
        """
        session = self._get_session()

        try:
            # 1. Provide raw bytes to rembg
            output_bytes = rembg.remove(image_bytes, session=session)
            
            # If a solid background color is requested, composite it using Pillow
            if bg_color:
                # Load the transparent image rembg just created
                fg_image = Image.open(io.BytesIO(output_bytes)).convert("RGBA")
                
                # Parse hex color and create a solid background image of the same size
                rgb_color = self._hex_to_rgb(bg_color)
                bg_image = Image.new("RGBA", fg_image.size, rgb_color + (255,))
                
                # Composite (paste the foreground over the background using the foreground's alpha channel as a mask)
                bg_image.paste(fg_image, (0, 0), fg_image)
                
                # Convert back to RGB for JPEG saving
                final_image = bg_image.convert("RGB")
                
                # Save to bytes
                out_io = io.BytesIO()
                final_image.save(out_io, format="JPEG", quality=90)
                return out_io.getvalue()
            
            # If no color requested, just return the raw transparent PNG bytes from rembg
            return output_bytes
            
        except Exception as e:
            logger.error(f"Error during background removal: {str(e)}")
            raise
