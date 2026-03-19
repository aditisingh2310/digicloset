import secrets
from fastapi import Header, HTTPException
from typing import Optional

from .storage import JSONStore

store = JSONStore()


def create_user(user_id: str, name: str, email: str, api_key: Optional[str] = None) -> dict:
    if not api_key:
        api_key = secrets.token_hex(16)
    user = {
        "user_id": user_id,
        "name": name,
        "email": email,
        "api_key": api_key,
        "roles": {},
    }
    store.save_user(user)
    return user


def assign_role(user_id: str, store_id: str, role: str) -> dict:
    user = store.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    roles = user.get("roles", {})
    role_list = roles.get(store_id, [])
    if role not in role_list:
        role_list.append(role)
    roles[store_id] = role_list
    user["roles"] = roles
    store.save_user(user)
    return user


def get_user_from_api_key(x_api_key: Optional[str] = Header(None)) -> dict:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-KEY header")
    user = store.get_user_by_api_key(x_api_key)
    if not user:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return user


def require_role(role: str):
    def _dependency(x_api_key: Optional[str] = Header(None)):
        user = get_user_from_api_key(x_api_key)
        roles = user.get("roles", [])
        if role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user

    return _dependency
