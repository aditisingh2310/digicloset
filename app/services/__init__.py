"""
Services package for DigiCloset growth and monetization features.

This package contains all the business logic services for:
- Revenue attribution and tracking
- AI usage metering and limits
- Observability and event logging
- Intelligent upgrade prompts
- Self-healing and reliability guards
"""

from .revenue_attribution import revenue_attribution, RevenueAttributionEngine
from .ai_metering import ai_metering, AIMeteringService
from .observability import observability, ObservabilityService
from .upgrade_prompts import upgrade_prompts, UpgradePromptsService
from .reliability_guard import reliability_guard, ReliabilityGuard

__all__ = [
    "revenue_attribution",
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