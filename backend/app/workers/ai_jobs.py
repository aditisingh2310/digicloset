from app.services.ai_image_pipeline import remove_background, enhance_image
from app.services.ai_text_generation import generate_alt_text, generate_tags_and_attributes

def process_product(product):
    bg = remove_background(product["image_path"])
    enhanced = enhance_image(bg)
    alt = generate_alt_text(product["title"])
    tags, attrs = generate_tags_and_attributes(product["title"])

    return {
        "enhanced": enhanced,
        "alt": alt,
        "tags": tags,
        "attributes": attrs
    }


def bulk_reanalyze(products: list):
    results = []
    for product in products:
        results.append(process_product(product))
    return results
