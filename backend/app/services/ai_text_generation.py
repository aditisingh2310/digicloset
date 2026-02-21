def generate_alt_text(product_title: str) -> str:
    return f"High-quality product image of {product_title} on a clean background"


def generate_tags_and_attributes(product_title: str):
    tags = product_title.lower().split(" ")
    attributes = {
        "material": "unknown",
        "style": "modern",
        "category": "apparel"
    }
    return tags, attributes
