def generate_seo_description(title: str, tags: list, attributes: dict) -> str:
    tag_line = ", ".join(tags[:5])
    attr_line = ", ".join(f"{k}: {v}" for k, v in attributes.items())

    return (
        f"{title} is a premium product designed for modern customers. "
        f"Featuring {tag_line}. Key attributes include {attr_line}. "
        "Optimized for search and conversions."
    )
