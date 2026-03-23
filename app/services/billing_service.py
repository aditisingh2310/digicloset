from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models import Shop, Subscription, UsageEvent, CreditBalance
from app.core.plans import PLANS
from app.services.shopify_client import ShopifyClient
from app.models.billing import SubscriptionRecord, UsageRecord


class StorageInterface:
    """Abstract storage interface for lightweight/in-memory usage."""

    async def get_subscription(self, shop: str):
        raise NotImplementedError()

    async def save_subscription(self, record) -> None:
        raise NotImplementedError()

    async def get_usage(self, shop: str):
        raise NotImplementedError()

    async def save_usage(self, usage) -> None:
        raise NotImplementedError()


class InMemoryStore(StorageInterface):
    def __init__(self):
        self.subs = {}
        self.usage = {}

    async def get_subscription(self, shop: str):
        return self.subs.get(shop)

    async def save_subscription(self, record) -> None:
        self.subs[record.shop_domain] = record

    async def get_usage(self, shop: str):
        return self.usage.get(shop)

    async def save_usage(self, usage) -> None:
        self.usage[usage.shop_domain] = usage

logger = logging.getLogger(__name__)


class BillingService:
    def __init__(self, shop_domain: str, access_token: str, db: Session, shopify_client: Optional[ShopifyClient] = None):
        self.shop_domain = shop_domain
        self.db = None
        self.store = None
        if isinstance(db, StorageInterface) or (
            hasattr(db, "get_subscription") and hasattr(db, "get_usage")
        ):
            self.store = db
            self._store_lock = asyncio.Lock()
        else:
            self.db = db
        self.client = shopify_client or ShopifyClient(shop_domain, access_token)

    async def ensure_shop(self) -> Shop:
        if self.db is None:
            raise RuntimeError("Database session not available")
        shop = self.db.query(Shop).filter(Shop.domain == self.shop_domain).first()
        if not shop:
            shop = Shop(domain=self.shop_domain, access_token=self.client.access_token)
            self.db.add(shop)
            self.db.commit()
            self.db.refresh(shop)
        return shop

    async def subscribe(self, plan_name: str) -> dict:
        if self.store is not None:
            if plan_name not in PLANS:
                raise ValueError(f"Invalid plan: {plan_name}")
            existing = await self.store.get_subscription(self.shop_domain)
            if existing and existing.status in ("active", "pending"):
                return {"confirmation_url": None, "subscription_id": existing.charge_id}
            trial_days = PLANS[plan_name]["trial_days"]
            record = SubscriptionRecord(
                shop_domain=self.shop_domain,
                plan_name=plan_name,
                status="pending",
                trial_ends_at=datetime.utcnow() + timedelta(days=trial_days) if trial_days else None,
            )
            await self.store.save_subscription(record)
            return {"confirmation_url": None, "subscription_id": record.charge_id}

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
        if self.store is not None:
            record = await self.store.get_subscription(self.shop_domain)
            if record is None:
                record = SubscriptionRecord(shop_domain=self.shop_domain, plan_name="starter")
            record.status = "active"
            record.charge_id = charge_id
            record.activated_at = datetime.utcnow()
            await self.store.save_subscription(record)
            return record
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
        if self.store is not None:
            sub = await self.store.get_subscription(self.shop_domain)
            return {
                "plan": sub.plan_name if sub else None,
                "status": sub.status if sub else "inactive",
                "credits": 0,
                "reset_date": None,
            }
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
        if self.store is not None:
            sub = await self.store.get_subscription(self.shop_domain)
            if not sub:
                return False
            if sub.status == "active":
                return True
            if sub.trial_ends_at and sub.trial_ends_at > datetime.utcnow():
                return True
            return False
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
        if self.store is not None:
            record = await self.store.get_subscription(self.shop_domain)
            if not record:
                return
            record.status = "cancelled"
            record.cancelled_at = datetime.utcnow()
            await self.store.save_subscription(record)
            return
        shop = await self.ensure_shop()
        sub = self.db.query(Subscription).filter(
            Subscription.shop_id == shop.id,
            Subscription.status.in_(["active", "pending"]),
        ).first()
        if not sub:
            return
        sub.status = "cancelled"
        sub.cancelled_at = datetime.utcnow()
        self.db.commit()
        logger.info("Cancelled subscription for %s", self.shop_domain)

    async def increment_usage(self, ai_calls: int = 0, products: int = 0) -> dict:
        if self.store is not None:
            async with self._store_lock:
                usage = await self.store.get_usage(self.shop_domain)
                if usage is None:
                    usage = UsageRecord(shop_domain=self.shop_domain)
                usage.ai_calls_this_month += int(ai_calls or 0)
                usage.products_processed_this_month += int(products or 0)
                usage.last_usage_at = datetime.utcnow()
                await self.store.save_usage(usage)
            return {"ai_calls": ai_calls, "products_processed": products}
        shop = await self.ensure_shop()
        now = datetime.utcnow()
        events = []
        if ai_calls:
            events.append(
                UsageEvent(
                    shop_id=shop.id,
                    event_type="ai_calls",
                    amount=float(ai_calls),
                    description="AI usage",
                    timestamp=now,
                )
            )
        if products:
            events.append(
                UsageEvent(
                    shop_id=shop.id,
                    event_type="products_processed",
                    amount=float(products),
                    description="Products processed",
                    timestamp=now,
                )
            )
        for event in events:
            self.db.add(event)
        if events:
            self.db.commit()
        return {"ai_calls": ai_calls, "products_processed": products}

    async def activate_charge(self, charge_id: str):
        """Backward-compatible alias for activate_subscription."""
        return await self.activate_subscription(charge_id)
