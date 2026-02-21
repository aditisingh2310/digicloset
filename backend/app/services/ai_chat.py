def explain_product_score(product: dict) -> str:
    issues = product.get("issues", [])
    if not issues:
        return "This product is well optimized."

    return (
        "This product can be improved. "
        "Main issues: " + ", ".join(issues)
    )
