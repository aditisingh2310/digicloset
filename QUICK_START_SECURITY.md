"""
QUICK START: Integrating Production Security into Your FastAPI App
===================================================================

This guide shows how to add the security implementations to your existing
FastAPI application in 15 minutes.

PREREQUISITE: Redis running locally or accessible
  docker run -d -p 6379:6379 redis:7-alpine


STEP 1: Create your secure app (2 minutes)
============================================

Create app/main.py or update your existing main.py:

import logging
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

# Import security modules
from app.middleware import RateLimitMiddleware, RateLimiter, TenantMiddleware, get_shop_id
from app.utils import (
    setup_pii_safe_logging,
    ErrorResponse,
    RequestIDMiddleware,
)
from app.utils.errors import (
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)

# Create app
app = FastAPI(title="DigiCloset API", version="2.0.0")

# -------- MIDDLEWARE STACK (in order) --------

# 1. Request ID tracking
app.add_middleware(RequestIDMiddleware)

# 2. Tenant enforcement
app.add_middleware(
    TenantMiddleware,
    require_for_paths=["/api/"],          # Enforce on /api/*
    skip_paths=["/health", "/docs"],      # Skip these
)

# 3. Rate limiting
rate_limiter = RateLimiter()
app.add_middleware(RateLimitMiddleware, limiter=rate_limiter)

# -------- EXCEPTION HANDLERS --------

app.add_exception_handler(Exception, general_exception_handler)
from starlette.exceptions import HTTPException as StarletteHTTPException
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# -------- LOGGING --------

logger = setup_pii_safe_logging(__name__)

# Use it like this (automatically masks tokens):
# safe_log("User login", logger=logger, shop_id=shop_id, token=token)


STEP 2: Update your endpoints (5 minutes)
===========================================

For each existing endpoint that accesses tenant data, add shop_id dependency:

BEFORE:
-------
@app.get("/api/v1/products")
async def list_products(skip: int = 0, limit: int = 10):
    products = db.query(Product).offset(skip).limit(limit).all()
    return products

AFTER:
------
from fastapi import Depends, Request
from app.utils import get_request_id

@app.get("/api/v1/products")
async def list_products(
    request: Request,
    shop_id: str = Depends(get_shop_id),  # Add this line
    skip: int = 0,
    limit: int = 10,
):
    # Add shop_id filter to query
    products = db.query(Product).filter(
        Product.shop_id == shop_id  # Add this line
    ).offset(skip).limit(limit).all()
    
    # Optionally add request_id to response
    return {
        "request_id": get_request_id(request),
        "products": products,
    }

That's it! Rate limiting, tenant isolation, and error handling are automatic.


STEP 3: Add input validation for heavy endpoints (3 minutes)
==============================================================

For AI endpoints, image uploads, or bulk operations:

BEFORE:
-------
@app.post("/api/v1/ai/analyze")
async def analyze(file: UploadFile = File(...)):
    image_data = await file.read()
    result = await ai_service.analyze(image_data)
    return result

AFTER:
------
from fastapi import Depends, Request, File, UploadFile
from app.utils import PayloadValidator, TimeoutGuard, get_request_id

@app.post("/api/v1/ai/analyze")
@TimeoutGuard.timeout(120)  # Add timeout
async def analyze(
    request: Request,
    shop_id: str = Depends(get_shop_id),  # Add tenant
    file: UploadFile = File(...),
):
    # Validate image size and format
    PayloadValidator.validate_image_upload(file)
    
    image_data = await file.read()
    result = await ai_service.analyze(image_data)
    
    return {
        "request_id": get_request_id(request),
        "result": result,
    }


STEP 4: Replace logging calls (5 minutes, optional)
====================================================

Replace your logging to prevent token leaks:

BEFORE:
-------
import logging
logger = logging.getLogger(__name__)

logger.info(f"User {user_id} with token {token} logged in")
# BAD: Token is visible in logs!

AFTER:
------
from app.utils import setup_pii_safe_logging, safe_log

logger = setup_pii_safe_logging(__name__)

safe_log("User logged in", logger=logger, user_id=user_id, token=token)
# GOOD: Output is: User logged in | {"user_id": "123", "token": "***REDACTED***"}

For authentication/audit events:
------
from app.utils import AuditLogger

audit = AuditLogger()

@app.post("/api/auth/login")
async def login(credentials: dict):
    try:
        # Auth logic
        audit.log_authentication(shop_id, "oauth", success=True)
        return {"token": token}
    except:
        audit.log_authentication(shop_id, "oauth", success=False)
        raise


STEP 5: Set environment variables (1 minute)
===============================================

Create .env file:

# Redis (for rate limiting)
REDIS_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=INFO

That's it! Use defaults for everything else.


STEP 6: Verify it works (1 minute)
====================================

1. Start your app:
   uvicorn app.main:app --reload

2. Test health check (no auth):
   curl http://localhost:8000/health

3. Test API endpoint (with tenant):
   curl -H "X-Shop-ID: myshop123" http://localhost:8000/api/v1/products

4. Test rate limiting (hit endpoint 300+ times):
   for i in {1..350}; do
     curl -H "X-Shop-ID: myshop123" http://localhost:8000/api/v1/products
   done
   # Should see 429 Too Many Requests after 300 hits

5. Check logs for PII safety:
   cat app.log | grep token
   # Should see "***REDACTED***" not actual tokens


COMMON ISSUES & FIXES
======================

Issue: "Redis connection error"
Fix:
  1. Start Redis: docker run -d -p 6379:6379 redis:7-alpine
  2. Check REDIS_URL in .env
  3. Test: redis-cli ping

Issue: "Missing shop_id error"
Fix:
  1. Add Depends(get_shop_id) to your endpoint
  2. Pass X-Shop-ID header in requests
  3. Or pass shop_id as path param: /api/shop/{shop_id}/products

Issue: "Rate limit not working"
Fix:
  1. Verify RateLimitMiddleware is added
  2. Check order: it must be AFTER TenantMiddleware
  3. Test with: for i in {1..350}; do curl ...; done

Issue: "Tokens in logs"
Fix:
  1. Use safe_log() instead of logger.info()
  2. Set up PII formatter: setup_pii_safe_logging(__name__)
  3. Don't log request.headers directly

Issue: "Stack traces in error responses"
Fix:
  1. Register exception handlers:
     app.add_exception_handler(Exception, general_exception_handler)
  2. Use ErrorResponse.internal_error() instead of HTTPException
  3. Set show_detail=False in ErrorResponse methods


MINIMAL WORKING EXAMPLE
========================

File: main.py

from fastapi import FastAPI, Depends, Request
from app.middleware import RateLimitMiddleware, RateLimiter, TenantMiddleware, get_shop_id
from app.utils import setup_pii_safe_logging, RequestIDMiddleware, get_request_id
from app.utils.errors import general_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI()

# Middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(TenantMiddleware, require_for_paths=["/api/"])
app.add_middleware(RateLimitMiddleware, limiter=RateLimiter())

# Exception handlers
app.add_exception_handler(Exception, general_exception_handler)
app.add_exception_handler(StarletteHTTPException, general_exception_handler)

# Logging
logger = setup_pii_safe_logging(__name__)

# Endpoints
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/api/products")
async def list_products(
    request: Request,
    shop_id: str = Depends(get_shop_id),
):
    return {
        "request_id": get_request_id(request),
        "shop_id": shop_id,
        "products": [],
    }

# Run: uvicorn main:app --reload


WHAT YOU GET (After integration):
==================================

✓ Rate limiting:
  - 300 req/min for public APIs
  - 120 req/min for webhooks
  - 30 req/min for AI endpoints
  - Automatic 429 with Retry-After

✓ Tenant isolation:
  - shop_id required on all /api/* endpoints
  - Cannot read cross-tenant data
  - Automatic context cleanup

✓ PII-safe logging:
  - Tokens masked (***REDACTED***)
  - Domains masked (myshop → mys***)
  - Emails masked (user@example → u***@example)
  - No headers logged

✓ Standardized errors:
  - Consistent JSON schema
  - request_id tracking
  - No stack traces
  - Retry-After headers

✓ Abuse protection:
  - Image size limits (25MB)
  - AI timeout (120s)
  - Input validation
  - Suspicious pattern detection

All with ZERO changes to business logic ✓


NEXT: Production deployment
=============================

For production deployment, check:
  /workspaces/digicloset/app/middleware/SECURITY_SETUP.md

For detailed integration examples:
  /workspaces/digicloset/app/middleware/examples_integration.py

For full documentation:
  /workspaces/digicloset/PRODUCTION_SECURITY_IMPLEMENTATION.md
"""
