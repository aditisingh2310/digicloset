def detect_image_angle(image_url: str) -> str:
    """
    Deterministic placeholder.
    """
    if "front" in image_url:
        return "front"
    if "back" in image_url:
        return "back"
    if "detail" in image_url:
        return "detail"
    return "lifestyle"


def missing_angles(existing_angles: list):
    required = {"front", "back", "detail"}
    return list(required - set(existing_angles))
