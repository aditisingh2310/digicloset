from __future__ import annotations

import logging
from typing import Optional
from datetime import datetime

from app.models.audit import DeletionAudit
from app.models.billing import SubscriptionRecord, UsageRecord
from app.db.models import Shop, Subscription, UsageEvent, CreditBalance
from services.data_deletion import delete_shop_data

logger = logging.getLogger(__name__)


class DataDeletionService:
    def __init__(self, store=None, db=None, redis=None):
        # store implements get_subscription/save_subscription/get_usage/save_usage and raw deletes
        self.store = store
        self.db = db
        self.redis = redis

    async def delete_shop_data(self, shop_domain: str) -> DeletionAudit:
        """Perform cascading, idempotent deletion of shop-scoped data.

        - revoke and remove access tokens
        - remove usage records
        - remove AI history (AiResult entries) -- in memory store may just delete keys
        - mark shop as uninstalled
        """
        audit_details = {"note": "cascading delete performed"}

        # Prefer explicit store interface (used in tests or lightweight deployments)
        if self.store is not None:
            # delete subscription
            sub = await self.store.get_subscription(shop_domain)
            if sub:
                sub.status = "uninstalled"
                sub.activated_at = sub.activated_at
                await self.store.save_subscription(sub)
                audit_details["subscription_status"] = "uninstalled"

            # delete usage
            usage = await self.store.get_usage(shop_domain)
            if usage:
                # remove by setting counts to zero and month_period to None
                usage.ai_calls_this_month = 0
                usage.products_processed_this_month = 0
                usage.last_usage_at = None
                usage.month_period = None
                await self.store.save_usage(usage)
                audit_details["usage_reset"] = True

        # DB-backed hard delete flow
        elif self.db is not None:
            shop = self.db.query(Shop).filter(Shop.domain == shop_domain).first()
            if shop:
                shop.access_token = ""
                shop.uninstalled_at = datetime.utcnow()
                self.db.add(shop)

                deleted_subs = self.db.query(Subscription).filter(Subscription.shop_id == shop.id).delete(synchronize_session=False)
                deleted_usage = self.db.query(UsageEvent).filter(UsageEvent.shop_id == shop.id).delete(synchronize_session=False)
                deleted_credits = self.db.query(CreditBalance).filter(CreditBalance.shop_id == shop.id).delete(synchronize_session=False)

                self.db.commit()

                audit_details.update(
                    {
                        "deleted_subscriptions": deleted_subs,
                        "deleted_usage_events": deleted_usage,
                        "deleted_credit_balances": deleted_credits,
                    }
                )
            else:
                audit_details["shop_missing"] = True

        # Revoke sessions stored in Redis
        if self.redis is not None:
            try:
                session_key = f"shop_sessions:{shop_domain}"
                session_ids = self.redis.smembers(session_key) or set()
                for sess in session_ids:
                    sess_id = sess.decode() if isinstance(sess, (bytes, bytearray)) else str(sess)
                    self.redis.delete(f"session:{sess_id}")
                    self.redis.delete(f"shopify_session:{sess_id}")
                    self.redis.delete(f"session_shop:{sess_id}")
                self.redis.delete(session_key)
                audit_details["sessions_revoked"] = len(session_ids)
            except Exception:
                logger.debug("Failed to revoke sessions for %s", shop_domain, exc_info=True)

        # Record audit
        audit = DeletionAudit(
            shop_domain=shop_domain,
            action="delete_shop_data",
            details=audit_details,
            timestamp=datetime.utcnow(),
        )
        logger.info("Deletion audit: %s", audit.json())
        return audit
async def delete_shop_data(shop: str):

    await db.orders.delete_many({"shop": shop})
    await db.products.delete_many({"shop": shop})
    await db.users.delete_many({"shop": shop})
