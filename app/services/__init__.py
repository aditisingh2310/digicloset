"""Service exports for the DigiCloset backend."""

from .revenue_attribution import RevenueAttributionEngine, revenue_engine
from .ai_metering import AIMeteringService, ai_metering
from .observability import ObservabilityService, observability
from .upgrade_prompts import UpgradePromptsService, upgrade_prompts
from .reliability_guard import ReliabilityGuard, reliability_guard

# Backwards-compatible alias expected by older modules/tests
revenue_attribution = revenue_engine

__all__ = [
    "revenue_attribution",
    "revenue_engine",
    "RevenueAttributionEngine",
    "ai_metering",
    "AIMeteringService",
    "observability",
    "ObservabilityService",
    "upgrade_prompts",
    "UpgradePromptsService",
    "reliability_guard",
    "ReliabilityGuard",
]
