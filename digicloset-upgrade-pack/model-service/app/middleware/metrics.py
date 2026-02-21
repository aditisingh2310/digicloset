"""
Prometheus metrics middleware for the model-service.
Exposes /metrics endpoint for scraping and tracks per-endpoint latency histograms.
"""

import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# In-memory metrics store (lightweight alternative to prometheus_client for simplicity)
_metrics = {
    "requests_total": {},         # endpoint -> count
    "requests_errors": {},        # endpoint -> count
    "latency_seconds": {},        # endpoint -> list of latencies
}


class MetricsMiddleware(BaseHTTPMiddleware):
    """Records request count and latency per endpoint."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method
        key = f"{method} {path}"

        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start

        # Track request count
        _metrics["requests_total"][key] = _metrics["requests_total"].get(key, 0) + 1

        # Track errors (4xx/5xx)
        if response.status_code >= 400:
            _metrics["requests_errors"][key] = _metrics["requests_errors"].get(key, 0) + 1

        # Track latency (keep last 100 samples per endpoint)
        if key not in _metrics["latency_seconds"]:
            _metrics["latency_seconds"][key] = []
        samples = _metrics["latency_seconds"][key]
        samples.append(elapsed)
        if len(samples) > 100:
            _metrics["latency_seconds"][key] = samples[-100:]

        return response


def get_metrics_summary() -> dict:
    """Returns a summary of all collected metrics."""
    latency_summary = {}
    for key, samples in _metrics["latency_seconds"].items():
        if samples:
            latency_summary[key] = {
                "count": len(samples),
                "avg_ms": round(sum(samples) / len(samples) * 1000, 2),
                "max_ms": round(max(samples) * 1000, 2),
                "min_ms": round(min(samples) * 1000, 2),
            }

    return {
        "requests_total": _metrics["requests_total"],
        "requests_errors": _metrics["requests_errors"],
        "latency": latency_summary,
    }
