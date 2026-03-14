from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.db.models import Shop, Subscription, UsageEvent, CreditBalance
from app.core.plans import PLANS
from app.services.shopify_client import ShopifyClient

logger = logging.getLogger(__name__)


class BillingService:
    def __init__(self, shop_domain: str, access_token: str, db: Session, shopify_client: Optional[ShopifyClient] = None):
        self.shop_domain = shop_domain
        self.db = db
        self.client = shopify_client or ShopifyClient(shop_domain, access_token)

    async def ensure_shop(self) -> Shop:
        shop = self.db.query(Shop).filter(Shop.domain == self.shop_domain).first()
        if not shop:
            shop = Shop(domain=self.shop_domain, access_token=self.client.access_token)
            self.db.add(shop)
            self.db.commit()
            self.db.refresh(shop)
        return shop

    async def subscribe(self, plan_name: str) -> dict:
        if plan_name not in PLANS:
            raise ValueError(f"Invalid plan: {plan_name}")

        shop = await self.ensure_shop()
        plan = PLANS[plan_name]

        # Check existing subscription
        existing_sub = self.db.query(Subscription).filter(
            Subscription.shop_id == shop.id,
            Subscription.status.in_(["active", "pending"])
        ).first()

        if existing_sub:
            return {"confirmation_url": None, "subscription_id": existing_sub.id}

        # Create AppSubscription via GraphQL
        mutation = f"""
        mutation appSubscriptionCreate($name: String!, $price: Decimal!, $trialDays: Int, $returnUrl: URL!) {{
          appSubscriptionCreate(
            name: $name
            returnUrl: $returnUrl
            trialDays: $trialDays
            lineItems: [{{
              plan: {{
                appRecurringPricingDetails: {{
                  price: {{ amount: $price, currencyCode: USD }}
                  interval: {plan['billing_interval']}
                }}
              }}
            }}]
          ) {{
            userErrors {{
              field
              message
            }}
            confirmationUrl
            appSubscription {{
              id
            }}
          }}
        }}
        """

        variables = {
            "name": f"{plan_name.capitalize()} Plan",
            "price": plan["price"],
            "trialDays": plan["trial_days"],
            "returnUrl": f"https://yourapp.com/billing/activate?shop={self.shop_domain}"
        }

        resp = self.client.graphql_request(mutation, variables)
        data = resp.get("data", {}).get("appSubscriptionCreate", {})

        if data.get("userErrors"):
            raise Exception(f"Shopify error: {data['userErrors']}")

        confirmation_url = data.get("confirmationUrl")
        subscription_gid = data.get("appSubscription", {}).get("id")

        # Save pending subscription
        sub = Subscription(
            shop_id=shop.id,
            plan_name=plan_name,
            status="pending",
            trial_ends_at=datetime.utcnow() + timedelta(days=plan["trial_days"]) if plan["trial_days"] else None
        )
        self.db.add(sub)
        self.db.commit()

        return {"confirmation_url": confirmation_url, "subscription_id": sub.id}

    async def activate_subscription(self, charge_id: str) -> Subscription:
        shop = await self.ensure_shop()
        sub = self.db.query(Subscription).filter(
            Subscription.shop_id == shop.id,
            Subscription.status == "pending"
        ).first()

        if not sub:
            raise ValueError("No pending subscription found")

        sub.status = "active"
        sub.charge_id = charge_id
        sub.activated_at = datetime.utcnow()
        self.db.commit()

        # Assign credits
        plan = PLANS[sub.plan_name]
        credits = plan["credits"]
        if credits != float('inf'):
            balance = self.db.query(CreditBalance).filter(CreditBalance.shop_id == shop.id).first()
            if not balance:
                balance = CreditBalance(shop_id=shop.id, credits=credits, monthly_limit=credits, reset_date=datetime.utcnow() + timedelta(days=30))
                self.db.add(balance)
            else:
                balance.credits = credits
                balance.monthly_limit = credits
                balance.reset_date = datetime.utcnow() + timedelta(days=30)
            self.db.commit()

        return sub

    async def get_status(self) -> dict:
        shop = await self.ensure_shop()
        sub = self.db.query(Subscription).filter(
            Subscription.shop_id == shop.id,
            Subscription.status == "active"
        ).first()

        balance = self.db.query(CreditBalance).filter(CreditBalance.shop_id == shop.id).first()

        return {
            "plan": sub.plan_name if sub else None,
            "status": sub.status if sub else "inactive",
            "credits": balance.credits if balance else 0,
            "reset_date": balance.reset_date.isoformat() if balance and balance.reset_date else None
        }

    async def is_active_or_in_trial(self) -> bool:
        shop = await self.ensure_shop()
        sub = self.db.query(Subscription).filter(
            Subscription.shop_id == shop.id,
            Subscription.status.in_(["active", "pending"])
        ).first()

        if sub and sub.status == "active":
            return True

        if sub and sub.trial_ends_at and sub.trial_ends_at > datetime.utcnow():
            return True

        return False

    async def cancel_subscription(self) -> None:
        rec = await self.store.get_subscription(self.shop)
        if not rec:
            return
        rec.status = "cancelled"
        await self.store.save_subscription(rec)
        logger.info("Cancelled subscription for %s", self.shop)

    async def is_active_or_in_trial(self) -> bool:
        rec = await self.store.get_subscription(self.shop)
        if not rec:
            return False
        if rec.status == "active":
            return True
        if rec.trial_ends_at and rec.trial_ends_at > datetime.utcnow():
            return True
        return False

    async def increment_usage(self, ai_calls: int = 0, products: int = 0) -> UsageRecord:
        usage = await self.store.get_usage(self.shop)
        now = datetime.utcnow()
        ym = now.strftime("%Y-%m")
        if not usage or usage.month_period != ym:
            usage = UsageRecord(shop_domain=self.shop, ai_calls_this_month=0, products_processed_this_month=0, month_period=ym)
        usage.ai_calls_this_month += ai_calls
        usage.products_processed_this_month += products
        usage.last_usage_at = now
        await self.store.save_usage(usage)
        return usage
