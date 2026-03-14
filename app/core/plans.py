from __future__ import annotations

from typing import Dict


PLANS: Dict[str, dict] = {
    "starter": {
        "price": 19.0,
        "credits": 200,
        "billing_interval": "EVERY_30_DAYS",
        "trial_days": 7
    },
    "growth": {
        "price": 49.0,
        "credits": 1000,
        "billing_interval": "EVERY_30_DAYS",
        "trial_days": 7
    },
    "scale": {
        "price": 99.0,
        "credits": float('inf'),  # unlimited
        "billing_interval": "EVERY_30_DAYS",
        "trial_days": 7
    }
}
