import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
import io
import math

class ColorExtractor:
    # Standard fashion color palette mapping
    FASHION_COLORS = {
        "Black": (0, 0, 0),
        "White": (255, 255, 255),
        "Red": (255, 0, 0),
        "Green": (0, 128, 0),
        "Blue": (0, 0, 255),
        "Yellow": (255, 255, 0),
        "Cyan": (0, 255, 255),
        "Magenta": (255, 0, 255),
        "Silver": (192, 192, 192),
        "Gray": (128, 128, 128),
        "Maroon": (128, 0, 0),
        "Olive": (128, 128, 0),
        "Purple": (128, 0, 128),
        "Teal": (0, 128, 128),
        "Navy": (0, 0, 128),
        "Brown": (165, 42, 42),
        "Pink": (255, 192, 203),
        "Orange": (255, 165, 0),
        "Beige": (245, 245, 220),
        "Tan": (210, 180, 140)
    }

    def _closest_color_name(self, rgb):
        """Finds the closest fashion color name to the given RGB tuple using Euclidean distance."""
        r, g, b = rgb
        color_diffs = []
        for name, value in self.FASHION_COLORS.items():
            cr, cg, cb = value
            # Euclidean distance
            distance = math.sqrt((r - cr)**2 + (g - cg)**2 + (b - cb)**2)
            color_diffs.append((distance, name))
        return min(color_diffs)[1]
        
    def _rgb_to_hex(self, rgb):
        return '#%02x%02x%02x' % tuple(rgb)

    def extract_colors(self, image_bytes: bytes, num_colors=3):
        """
        Shrinks the image, removes the background color using edge sampling,
        and runs KMeans clustering to find the dominant garment colors.
        """
        # Load and vastly downsample image for pure speed
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        image = image.resize((50, 50), Image.Resampling.LANCZOS)
        
        # Convert to numpy array
        img_array = np.array(image)
        h, w, _ = img_array.shape
        
        # Heuristic Background Removal: Sample the 4 corners to find the likely background color
        tl = img_array[0, 0]
        tr = img_array[0, w-1]
        bl = img_array[h-1, 0]
        br = img_array[h-1, w-1]
        # Average the corners to guess the background
        bg_rgb = np.mean([tl, tr, bl, br], axis=0)

        # Flatten the image array into a list of pixels
        pixels = img_array.reshape(-1, 3)
        
        # Filter out pixels that are too close to the background color
        # Threshold: if euclidean distance is < 30, it's considered background
        foreground_pixels = []
        for pixel in pixels:
            dist = np.linalg.norm(pixel - bg_rgb)
            if dist > 30:
                foreground_pixels.append(pixel)
        
        foreground_pixels = np.array(foreground_pixels)
        
        # Fallback if image was entirely background (e.g. solid color)
        if len(foreground_pixels) < num_colors:
            foreground_pixels = pixels

        # Cluster the foreground pixels
        kmeans = KMeans(n_clusters=num_colors, n_init='auto', random_state=42)
        kmeans.fit(foreground_pixels)
        
        # Get the RGB centroids
        centroids = kmeans.cluster_centers_
        
        # Calculate the percentage of each cluster
        labels = list(kmeans.labels_)
        percent = []
        for i in range(len(centroids)):
            j = labels.count(i)
            j = j / len(labels)
            percent.append(j)
            
        # Combine percentages and colors, sort by most dominant
        colors = []
        for i in range(num_colors):
            rgb = (int(centroids[i][0]), int(centroids[i][1]), int(centroids[i][2]))
            colors.append({
                "hex": self._rgb_to_hex(rgb),
                "name": self._closest_color_name(rgb),
                "percentage": round(percent[i] * 100, 2)
            })
            
        # Sort descending by percentage
        colors = sorted(colors, key=lambda x: x['percentage'], reverse=True)
        return colors
