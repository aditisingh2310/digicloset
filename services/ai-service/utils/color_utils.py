"""Color analysis utilities for fashion recommendations."""

import logging
from typing import List, Tuple
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def get_dominant_colors(
    image: Image.Image,
    num_colors: int = 5
) -> List[Tuple[int, int, int]]:
    """
    Extract dominant colors from image using K-means clustering.
    
    Args:
        image: PIL Image
        num_colors: Number of dominant colors to extract
        
    Returns:
        List of RGB tuples
    """
    try:
        # Resize for faster processing
        small_image = image.resize((150, 150))
        pixels = np.array(small_image).reshape(-1, 3)
        
        # Remove white/near-white pixels (background)
        mask = np.sum(pixels, axis=1) < 750  # Sum of RGB < 750
        pixels = pixels[mask]
        
        if len(pixels) == 0:
            return [(128, 128, 128)]  # Default gray
        
        # Simple clustering using k-means
        from sklearn.cluster import KMeans
        
        kmeans = KMeans(n_clusters=min(num_colors, len(pixels)), random_state=42)
        kmeans.fit(pixels)
        
        colors = kmeans.cluster_centers_.astype(int)
        return [tuple(color) for color in colors]
    
    except ImportError:
        logger.warning("sklearn not available, using simpler color extraction")
        return extract_colors_simple(image, num_colors)
    except Exception as e:
        logger.error(f"Failed to extract dominant colors: {e}")
        return [(128, 128, 128)]


def extract_colors_simple(
    image: Image.Image,
    num_colors: int = 5
) -> List[Tuple[int, int, int]]:
    """
    Simple color extraction without sklearn (fallback method).
    
    Args:
        image: PIL Image
        num_colors: Number of colors
        
    Returns:
        List of RGB tuples
    """
    # Quantize to reduce colors
    image_small = image.resize((100, 100))
    image_quantized = image_small.quantize(colors=num_colors)
    
    colors = image_quantized.getpalette()[:num_colors * 3]
    color_list = [
        tuple(colors[i:i+3]) for i in range(0, len(colors), 3)
    ]
    return color_list


def rgb_to_hsv(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """Convert RGB to HSV color space."""
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    mx = max(r, g, b)
    mn = min(r, g, b)
    df = mx - mn
    
    if mx == mn:
        h = 0
    elif mx == r:
        h = (60 * ((g - b) / df) + 360) % 360
    elif mx == g:
        h = (60 * ((b - r) / df) + 120) % 360
    else:
        h = (60 * ((r - g) / df) + 240) % 360
    
    s = 0 if mx == 0 else (df / mx)
    v = mx
    
    return h, s, v


def color_similarity(
    color1: Tuple[int, int, int],
    color2: Tuple[int, int, int]
) -> float:
    """
    Compute color similarity (0-1) between two RGB colors.
    
    Uses HSV color space for better perceptual similarity.
    
    Args:
        color1: RGB tuple
        color2: RGB tuple
        
    Returns:
        Similarity score (1.0 = identical, 0.0 = very different)
    """
    h1, s1, v1 = rgb_to_hsv(*color1)
    h2, s2, v2 = rgb_to_hsv(*color2)
    
    # Hue difference (circular)
    hue_diff = min(abs(h1 - h2), 360 - abs(h1 - h2)) / 180.0
    saturation_diff = abs(s1 - s2)
    value_diff = abs(v1 - v2)
    
    # Weighted difference
    diff = (hue_diff * 0.5 + saturation_diff * 0.25 + value_diff * 0.25)
    
    return 1.0 - diff


def get_color_palette_similarity(
    colors1: List[Tuple[int, int, int]],
    colors2: List[Tuple[int, int, int]]
) -> float:
    """
    Compute similarity between two color palettes.
    
    Args:
        colors1: List of RGB colors
        colors2: List of RGB colors
        
    Returns:
        Similarity score (0-1)
    """
    if not colors1 or not colors2:
        return 0.5
    
    max_similarity = 0.0
    
    # Match each color in colors1 with best match in colors2
    for c1 in colors1[:3]:  # Use top 3 colors
        for c2 in colors2[:3]:
            sim = color_similarity(c1, c2)
            max_similarity = max(max_similarity, sim)
    
    return max_similarity / len(colors1[:3])
