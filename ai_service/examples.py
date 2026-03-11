"""
Example usage of the Shopify Fashion Recommendation Engine.

This script demonstrates:
1. Indexing a product catalog
2. Generating recommendations
3. Retrieving similar items
4. Getting outfit suggestions
"""

import json
import time
import asyncio
from typing import List, Dict
import requests
import numpy as np

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
REQUEST_TIMEOUT = 30


class RecommendationEngineClient:
    """Client for interacting with recommendation engine API."""
    
    def __init__(self, base_url: str = BASE_URL):
        """Initialize client."""
        self.base_url = base_url
        self.session = requests.Session()
    
    def health_check(self) -> Dict:
        """Check service health."""
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Health check failed: {e}")
            return None
    
    def index_catalog(self, products: List[Dict], batch_size: int = 32) -> Dict:
        """Index a list of products."""
        try:
            response = self.session.post(
                f"{self.base_url}/index-catalog",
                json={
                    "products": products,
                    "batch_size": batch_size
                },
                timeout=REQUEST_TIMEOUT * 2  # Longer timeout for indexing
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Indexing failed: {e}")
            return None
    
    def recommend_similar(
        self,
        product_id: int,
        top_k: int = 10,
        exclude_category: bool = False
    ) -> Dict:
        """Get visually similar products."""
        try:
            response = self.session.get(
                f"{self.base_url}/recommend/similar",
                params={
                    "product_id": product_id,
                    "top_k": top_k,
                    "exclude_category": exclude_category
                },
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Similarity search failed: {e}")
            return None
    
    def recommend_style(
        self,
        product_id: int,
        top_k: int = 5
    ) -> Dict:
        """Get style-compatible products."""
        try:
            response = self.session.get(
                f"{self.base_url}/recommend/style",
                params={
                    "product_id": product_id,
                    "top_k": top_k
                },
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Style recommendation failed: {e}")
            return None
    
    def recommend_outfit(
        self,
        product_id: int,
        max_items: int = 4
    ) -> Dict:
        """Get complete outfit recommendation."""
        try:
            response = self.session.get(
                f"{self.base_url}/recommend/outfit",
                params={
                    "product_id": product_id,
                    "max_items": max_items
                },
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Outfit recommendation failed: {e}")
            return None


def create_sample_catalog() -> List[Dict]:
    """Create a sample fashion product catalog for testing."""
    
    # Real Shopify product examples
    catalog = [
        # Tops
        {
            "id": 1,
            "title": "Classic White Cotton T-Shirt",
            "description": "Premium 100% cotton white t-shirt, perfect for casual wear. Comfortable fit with crew neckline.",
            "image_url": "https://via.placeholder.com/400?text=White+T-Shirt",
            "category": "shirt",
            "tags": ["casual", "basic", "white", "cotton"]
        },
        {
            "id": 2,
            "title": "Navy Blue Button-Up Shirt",
            "description": "Formal navy blue button-up shirt with long sleeves. Perfect for business casual.",
            "image_url": "https://via.placeholder.com/400?text=Blue+Shirt",
            "category": "shirt",
            "tags": ["formal", "navy", "business"]
        },
        {
            "id": 3,
            "title": "Vintage Graphic T-Shirt",
            "description": "Retro design graphic t-shirt in black. Soft vintage feel with trendy graphic print.",
            "image_url": "https://via.placeholder.com/400?text=Graphic+Tee",
            "category": "t-shirt",
            "tags": ["casual", "graphic", "vintage", "black"]
        },
        {
            "id": 4,
            "title": "Cozy Grey Sweater",
            "description": "Warm and comfortable grey sweater. Perfect for autumn and winter. Crew neck design.",
            "image_url": "https://via.placeholder.com/400?text=Grey+Sweater",
            "category": "sweater",
            "tags": ["warm", "grey", "casual", "comfortable"]
        },
        {
            "id": 5,
            "title": "Red Wool Cardigan",
            "description": "Elegant red wool cardigan with buttons. Great layering piece for any outfit.",
            "image_url": "https://via.placeholder.com/400?text=Red+Cardigan",
            "category": "sweater",
            "tags": ["elegant", "red", "wool", "layering"]
        },
        
        # Bottoms
        {
            "id": 6,
            "title": "Classic Blue Denim Jeans",
            "description": "Timeless blue denim jeans with straight leg fit. High quality fabric with stretch.",
            "image_url": "https://via.placeholder.com/400?text=Blue+Jeans",
            "category": "pants",
            "tags": ["casual", "denim", "blue", "classic"]
        },
        {
            "id": 7,
            "title": "Black Skinny Jeans",
            "description": "Sleek black skinny jeans with tapered ankle. Modern silhouette for contemporary style.",
            "image_url": "https://via.placeholder.com/400?text=Black+Jeans",
            "category": "pants",
            "tags": ["trendy", "black", "skinny", "modern"]
        },
        {
            "id": 8,
            "title": "Grey Trousers",
            "description": "Professional grey trousers for business wear. Tailored fit with pleated front.",
            "image_url": "https://via.placeholder.com/400?text=Grey+Trousers",
            "category": "pants",
            "tags": ["formal", "grey", "business", "professional"]
        },
        {
            "id": 9,
            "title": "Black Mini Skirt",
            "description": "Chic black mini skirt. Versatile piece that works with many tops.",
            "image_url": "https://via.placeholder.com/400?text=Black+Skirt",
            "category": "skirt",
            "tags": ["trendy", "black", "mini", "versatile"]
        },
        
        # Outerwear
        {
            "id": 10,
            "title": "Black Leather Jacket",
            "description": "Classic black leather jacket. Timeless piece for adding edge to any outfit.",
            "image_url": "https://via.placeholder.com/400?text=Leather+Jacket",
            "category": "jacket",
            "tags": ["classic", "black", "leather", "edge"]
        },
        {
            "id": 11,
            "title": "Denim Jacket",
            "description": "Casual denim jacket in light blue. Perfect for layering over t-shirts.",
            "image_url": "https://via.placeholder.com/400?text=Denim+Jacket",
            "category": "jacket",
            "tags": ["casual", "denim", "light-blue", "layering"]
        },
        {
            "id": 12,
            "title": "Wool Coat",
            "description": "Warm wool coat in camel color. Elegant and practical for cold weather.",
            "image_url": "https://via.placeholder.com/400?text=Wool+Coat",
            "category": "jacket",
            "tags": ["warm", "camel", "wool", "elegant"]
        },
        
        # Dresses
        {
            "id": 13,
            "title": "Black Evening Dress",
            "description": "Elegant black evening dress with long sleeves. Perfect for formal events.",
            "image_url": "https://via.placeholder.com/400?text=Evening+Dress",
            "category": "dress",
            "tags": ["formal", "black", "elegant", "evening"]
        },
        {
            "id": 14,
            "title": "Floral Summer Dress",
            "description": "Light and breezy floral summer dress. Perfect for warm weather.",
            "image_url": "https://via.placeholder.com/400?text=Floral+Dress",
            "category": "dress",
            "tags": ["summer", "floral", "breezy", "casual"]
        },
        
        # Shoes
        {
            "id": 15,
            "title": "White Sneakers",
            "description": "Classic white canvas sneakers. Comfortable for everyday wear.",
            "image_url": "https://via.placeholder.com/400?text=White+Sneakers",
            "category": "shoes",
            "tags": ["casual", "white", "sneakers", "comfortable"]
        },
        {
            "id": 16,
            "title": "Black High Heels",
            "description": "Elegant black high heels. Perfect for formal occasions.",
            "image_url": "https://via.placeholder.com/400?text=High+Heels",
            "category": "heels",
            "tags": ["formal", "black", "heels", "elegant"]
        },
        {
            "id": 17,
            "title": "Brown Leather Boots",
            "description": "Comfortable brown leather boots. Great for casual or business wear.",
            "image_url": "https://via.placeholder.com/400?text=Leather+Boots",
            "category": "shoes",
            "tags": ["versatile", "brown", "leather", "comfortable"]
        },
        {
            "id": 18,
            "title": "Flat Sandals",
            "description": "Comfortable flat sandals in tan. Perfect for summer.",
            "image_url": "https://via.placeholder.com/400?text=Sandals",
            "category": "flats",
            "tags": ["summer", "tan", "comfortable", "casual"]
        },
        
        # Accessories
        {
            "id": 19,
            "title": "Black Leather Belt",
            "description": "Classic black leather belt. Essential accessory for any wardrobe.",
            "image_url": "https://via.placeholder.com/400?text=Leather+Belt",
            "category": "belt",
            "tags": ["classic", "black", "leather", "accessory"]
        },
        {
            "id": 20,
            "title": "Brown Leather Handbag",
            "description": "Stylish brown leather handbag. Perfect for daily use.",
            "image_url": "https://via.placeholder.com/400?text=Handbag",
            "category": "bag",
            "tags": ["brown", "leather", "handbag", "stylish"]
        },
    ]
    
    return catalog


def print_section(title: str):
    """Print section header."""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def main():
    """Main example execution."""
    
    print("\n🎨 Shopify Fashion AI Recommendation Engine - Example Usage\n")
    
    client = RecommendationEngineClient()
    
    # 1. Health Check
    print_section("1. Health Check")
    health = client.health_check()
    if health:
        print(f"✓ Service Status: {health['status']}")
        print(f"✓ Device: {health['device']}")
        print(f"✓ Model: {health['model']}")
        print(f"✓ Products Indexed: {health['indexed_products']}")
    else:
        print("✗ Failed to connect to service")
        print("  Make sure the service is running: python main.py")
        return
    
    # 2. Index Catalog
    print_section("2. Indexing Product Catalog")
    catalog = create_sample_catalog()
    print(f"Indexing {len(catalog)} products...")
    
    start_time = time.time()
    index_result = client.index_catalog(catalog, batch_size=10)
    index_time = time.time() - start_time
    
    if index_result:
        print(f"✓ Indexing Complete ({index_time:.2f}s)")
        print(f"  Total Products: {index_result['total']}")
        print(f"  Successful: {index_result['successful']}")
        print(f"  Failed: {index_result['failed']}")
        print(f"  Index Size: {index_result['index_size']}")
        if index_result['failed_products']:
            print(f"  Failed Products: {index_result['failed_products'][:3]}")
    else:
        print("✗ Indexing failed")
        return
    
    # 3. Visual Similarity Search
    print_section("3. Visual Similarity Search")
    print("Finding products similar to: 'Classic White Cotton T-Shirt' (ID: 1)")
    
    similar = client.recommend_similar(product_id=1, top_k=5)
    if similar:
        print(f"\n✓ Found {similar['total_count']} similar products:")
        for i, rec in enumerate(similar['recommendations'], 1):
            score = rec.get('similarity', 0) * 100
            print(f"  {i}. {rec['title']} (ID: {rec['product_id']}) - {score:.1f}% similar")
    
    # 4. Style Matching
    print_section("4. Style-Compatible Recommendations")
    print("Finding items that complement: 'Classic White Cotton T-Shirt' (ID: 1)")
    
    style = client.recommend_style(product_id=1, top_k=5)
    if style:
        print(f"\n✓ Found {style['total_count']} compatible items:")
        for i, rec in enumerate(style['recommendations'], 1):
            score = rec.get('compatibility_score', 0) * 100
            print(f"  {i}. {rec['title']} ({rec['category']}) - {score:.1f}% compatible")
    
    # 5. Complete Outfit
    print_section("5. Complete the Look - Outfit Generation")
    print("Generating outfit based on: 'Classic White Cotton T-Shirt' (ID: 1)")
    
    outfit = client.recommend_outfit(product_id=1, max_items=4)
    if outfit and "error" not in outfit:
        print(f"\n✓ Generated Outfit (Score: {outfit['outfit_score']:.2f})")
        print(f"  Total Items: {outfit['total_items']}")
        print("\n  Items:")
        for i, item in enumerate(outfit['outfit_items'], 1):
            role = item.get('role', 'item')
            print(f"    {i}. {item['title']} ({item['category'].capitalize()}) - {role}")
    else:
        print("✗ Outfit generation failed")
    
    # 6. Different Product Example
    print_section("6. Outfit Generation - Dress Example")
    print("Generating outfit based on: 'Black Evening Dress' (ID: 13)")
    
    outfit_dress = client.recommend_outfit(product_id=13, max_items=4)
    if outfit_dress and "error" not in outfit_dress:
        print(f"\n✓ Generated Outfit (Score: {outfit_dress['outfit_score']:.2f})")
        print(f"  Total Items: {outfit_dress['total_items']}")
        print("\n  Items:")
        for i, item in enumerate(outfit_dress['outfit_items'], 1):
            role = item.get('role', 'item')
            print(f"    {i}. {item['title']} ({item['category'].capitalize()}) - {role}")
    
    # 7. Performance Summary
    print_section("7. Performance Summary")
    print(f"✓ Index Time: {index_time:.2f}s for {len(catalog)} products")
    print(f"✓ Products/sec: {len(catalog)/index_time:.1f}")
    print(f"✓ API Endpoint: {BASE_URL}")
    print(f"✓ Docs: http://localhost:8000/docs")
    
    print("\n" + "="*60)
    print("  Example completed successfully! 🎉")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
