from __future__ import annotations

from datetime import datetime
from typing import Dict

from app.services.billing_service import BillingService


class OnboardingService:
    def __init__(self, billing_service: BillingService):
        self.billing = billing_service

    async def status(self) -> Dict:
        sub = await self.billing.store.get_subscription(self.billing.shop_domain)
        usage = await self.billing.store.get_usage(self.billing.shop_domain)
        plan = sub.plan_name if sub else "starter"
        trial_days_remaining = None
        if sub and sub.trial_ends_at:
            delta = sub.trial_ends_at - datetime.utcnow()
            trial_days_remaining = max(0, delta.days)

        usage_remaining = None
        plan_conf = {}
        # lookup plan config if available
        try:
            from app.core.plans import PLANS

            plan_conf = PLANS.get(plan, {})
        except Exception:
            plan_conf = {}

        if usage:
            limit = plan_conf.get("credits")
            if limit == float("inf"):
                usage_remaining = "unlimited"
            else:
                usage_remaining = (limit - usage.ai_calls_this_month) if limit is not None else None

        onboarding_complete = bool(sub and sub.status in ("active", "cancelled"))

        return {
            "trial_days_remaining": trial_days_remaining,
            "usage_remaining": usage_remaining,
            "subscription_active": (sub.status == "active") if sub else False,
            "onboarding_complete": onboarding_complete,
        }
