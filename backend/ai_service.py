from inference_service.main import app, health as health_check  # re-export for compatibility


def train_on_merchant_data(data, allow_training: bool = False):
    if not allow_training:
        return None

    # existing training logic
MAX_INFERENCE_TIME_MS = 300

def run_inference(payload=None, timeout_ms: int = MAX_INFERENCE_TIME_MS):
    """Placeholder inference function for legacy imports."""
    return {"ok": True, "timeout_ms": timeout_ms, "payload": payload}
