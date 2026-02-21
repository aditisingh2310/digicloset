"""
Image preprocessing utilities for the model-service.
Auto-resizes and normalizes images before passing them through the ML pipeline
to reduce compute load and ensure consistent input.
"""

import io
import logging
import hashlib
from PIL import Image

logger = logging.getLogger(__name__)

MAX_DIMENSION = 512  # Maximum width or height before resize


def compute_image_hash(image_bytes: bytes) -> str:
    """Compute a SHA-256 hash of the raw image bytes for cache keying."""
    return hashlib.sha256(image_bytes).hexdigest()


def preprocess_image(image_bytes: bytes, max_dim: int = MAX_DIMENSION) -> bytes:
    """
    Preprocesses an image for ML inference:
    1. Converts to RGB (strips alpha, handles grayscale).
    2. Resizes to fit within max_dim x max_dim while preserving aspect ratio.
    3. Re-encodes as JPEG for consistency.
    Returns the preprocessed image as bytes.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        original_size = img.size

        # Only resize if the image exceeds the max dimension
        if img.width > max_dim or img.height > max_dim:
            img.thumbnail((max_dim, max_dim), Image.LANCZOS)
            logger.info(f"Resized image from {original_size} to {img.size}")

        # Re-encode as JPEG
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue()

    except Exception as e:
        logger.warning(f"Image preprocessing failed, passing through original: {e}")
        return image_bytes


def preprocess_to_pil(image_bytes: bytes, max_dim: int = MAX_DIMENSION) -> Image.Image:
    """
    Same as preprocess_image but returns a PIL Image object directly.
    Useful when the downstream consumer (e.g. OpenCLIP) can accept PIL.
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    if img.width > max_dim or img.height > max_dim:
        img.thumbnail((max_dim, max_dim), Image.LANCZOS)
    return img
