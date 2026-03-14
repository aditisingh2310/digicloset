import redis
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

class RedisSessionStorage:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)

    def store_session(self, session_id: str, session_data: Dict[str, Any], expires_in: int = 3600):
        """Store session data with expiration."""
        self.redis.setex(f"shopify_session:{session_id}", expires_in, json.dumps(session_data))

    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session data."""
        data = self.redis.get(f"shopify_session:{session_id}")
        if data:
            return json.loads(data)
        return None

    def delete_session(self, session_id: str):
        """Delete session."""
        self.redis.delete(f"shopify_session:{session_id}")

# For Shopify API compatibility, implement the interface
class ShopifySessionStorage:
    def __init__(self, redis_storage: RedisSessionStorage):
        self.redis = redis_storage

    async def storeSession(self, session):
        data = {
            "id": session.id,
            "shop": session.shop,
            "state": session.state,
            "isOnline": session.isOnline,
            "accessToken": session.accessToken,
            "scope": session.scope
        }
        expires_in = 3600 * 24 * 30  # 30 days
        self.redis.store_session(session.id, data, expires_in)

    async def loadSession(self, id):
        data = self.redis.load_session(id)
        if data:
            # Reconstruct session object
            return Session(data)
        return None

    async def deleteSession(self, id):
        self.redis.delete_session(id)

class Session:
    def __init__(self, data):
        self.id = data["id"]
        self.shop = data["shop"]
        self.state = data["state"]
        self.isOnline = data["isOnline"]
        self.accessToken = data["accessToken"]
        self.scope = data["scope"]