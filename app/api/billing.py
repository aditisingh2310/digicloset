from __future__ import annotations

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from app.db.models import SessionLocal, Shop

from app.services.billing_service import BillingService

router = APIRouter(prefix="/billing", tags=["billing"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/subscribe")
async def subscribe(request: Request, plan: str = "starter", db: Session = Depends(get_db)):
    tenant = getattr(request.state, "tenant", None)
    if not tenant:
        raise HTTPException(status_code=401, detail="Missing tenant")

    svc = BillingService(tenant.shop_domain, tenant.access_token, db)
    try:
        result = await svc.subscribe(plan)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/status")
async def billing_status(request: Request, db: Session = Depends(get_db)):
    tenant = getattr(request.state, "tenant", None)
    if not tenant:
        raise HTTPException(status_code=401, detail="Missing tenant")

    svc = BillingService(tenant.shop_domain, tenant.access_token, db)
    try:
        status = await svc.get_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/webhook")
async def billing_webhook(request: Request, db: Session = Depends(get_db)):
    # Verify HMAC signature
    # For now, placeholder
    payload = await request.json()
    topic = payload.get("topic")
    shop_domain = request.headers.get("x-shopify-shop-domain")

    if not shop_domain:
        raise HTTPException(status_code=400, detail="Missing shop domain")

    # Get access token from db
    shop = db.query(Shop).filter(Shop.domain == shop_domain).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    svc = BillingService(shop_domain, shop.access_token, db)

    if topic == "app/subscriptions/update":
        # Handle subscription updates
        pass
    elif topic == "app/uninstalled":
        # Handle uninstall
        pass

    return {"status": "ok"}

# Activation endpoint after user approves
@router.get("/activate")
async def activate_subscription(charge_id: str, shop: str, db: Session = Depends(get_db)):
    svc = BillingService(shop, "", db)  # access_token will be fetched
    try:
        sub = await svc.activate_subscription(charge_id)
        return {"status": "activated", "plan": sub.plan_name}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
