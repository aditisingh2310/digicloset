"""
Production security dependencies for FastAPI multi-tenant applications.

Add these to your requirements.txt or pyproject.toml
"""

# Core FastAPI
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
pydantic-settings>=2.0.0

# Rate Limiting & Caching
redis>=5.0.0
aioredis>=2.0.0  # Async Redis support

# Async utilities
asyncio-contextmanager>=1.0.0

# Security & Validation
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
cryptography>=41.0.0

# Logging (PII handling)
python-json-logger>=2.0.7

# Request/Response handling
httpx>=0.25.0
requests>=2.31.0

# Type hints
typing-extensions>=4.8.0

# Testing (optional but recommended)
pytest>=7.4.0
pytest-asyncio>=0.21.0
httpx[cli]>=0.25.0

# Development (optional)
black>=23.0.0
flake8>=6.0.0
mypy>=1.5.0
isort>=5.12.0

# Monitoring (recommended for production)
prometheus-client>=0.18.0
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
opentelemetry-exporter-jaeger-thrift>=1.20.0

"""
=============================================================================
INSTALLATION INSTRUCTIONS
=============================================================================

Option 1: Using pip
-------------------
pip install -r requirements.txt

Option 2: Using pyproject.toml
------------------------------
poetry install

Option 3: Minimal production setup
----------------------------------
pip install fastapi uvicorn redis aioredis pydantic

=============================================================================
REDIS SETUP (For Rate Limiting)
=============================================================================

Local development:
    docker run -d -p 6379:6379 redis:7-alpine

Docker Compose example:
    services:
      redis:
        image: redis:7-alpine
        ports:
          - "6379:6379"
        volumes:
          - redis_data:/data
      api:
        build: .
        environment:
          REDIS_URL: redis://redis:6379/0
        ports:
          - "8000:8000"
        depends_on:
          - redis
    volumes:
      redis_data:

Production recommendation:
    - Use Redis Cluster for HA
    - Use Redis Sentinel for failover
    - Set appropriate TTL and eviction policies
    - Monitor memory usage and hit rates

=============================================================================
CONFIGURATION EXAMPLES
=============================================================================

Create a .env file for development:

    # Application
    ENVIRONMENT=development
    DEBUG=true
    LOG_LEVEL=DEBUG
    
    # Redis (rate limiting)
    REDIS_URL=redis://localhost:6379/0
    REDIS_TIMEOUT=5
    
    # Rate Limiting
    RATE_LIMIT_PUBLIC_RPM=300
    RATE_LIMIT_WEBHOOK_RPM=120
    RATE_LIMIT_AI_HEAVY_RPM=30
    
    # Abuse Protection
    MAX_REQUEST_SIZE=52428800  # 50MB
    MAX_IMAGE_SIZE=26214400    # 25MB
    MAX_AI_INPUT_LENGTH=10000
    MAX_SKU_LIST_LENGTH=1000
    TIMEOUT_API_HEAVY=120
    
    # Logging
    LOG_FORMAT=json
    LOG_SENSITIVE=false  # Enable PII masking

For production, use proper configuration management:
    - Use AWS Secrets Manager, HashiCorp Vault, or similar
    - Never commit .env files
    - Use environment variables with defaults
    - Rotate secrets regularly

=============================================================================
VERIFICATION CHECKLIST
=============================================================================

Before deploying to production, verify:

Rate Limiting:
  ✓ Redis is accessible and healthy
  ✓ RateLimitMiddleware is added to app
  ✓ Rate limit categories are appropriate for your workload
  ✓ Retry-After headers are sent (check 429 responses)

Tenant Isolation:
  ✓ TenantMiddleware is added
  ✓ All /api/* endpoints have Depends(get_shop_id)
  ✓ TenantContext is cleared after each request
  ✓ Test cross-tenant access prevention (should fail)

Logging:
  ✓ PII masking is enabled
  ✓ Tokens are never logged in plaintext
  ✓ Email addresses are masked
  ✓ Shop domains are partially masked
  ✓ Sensitive headers are not logged

Error Handling:
  ✓ Stack traces are never returned in 5xx responses
  ✓ request_id is included in all error responses
  ✓ Error codes are consistent and documented
  ✓ Retry-After is provided with 429 responses

Abuse Protection:
  ✓ Large uploads are rejected (413)
  ✓ AI endpoints have input length limits
  ✓ Timeouts prevent resource exhaustion
  ✓ Suspicious patterns are detected
  ✓ SKU lists are validated

=============================================================================
MONITORING & ALERTING
=============================================================================

Key metrics to monitor:

Rate Limiting:
  - Rate limit hits per shop/IP
  - Redis connection pool health
  - Cache hit/miss ratios

Tenant Isolation:
  - Cross-tenant access attempts (should be 0)
  - Missing shop_id errors

Logging:
  - Sensitive data detected (tokens, emails, etc.)
  - Log volume and storage costs

Error Handling:
  - 5xx error rate
  - Error codes distribution
  - request_id traceability

Abuse Protection:
  - Payload size rejections (413)
  - Input validation failures
  - Timeout occurrences
  - Suspicious pattern detections

Recommended alerting thresholds:
  - Rate limit 429s > 5% of traffic -> investigate
  - Cross-tenant access attempts > 0 -> immediate alert
  - 5xx errors > 1% -> investigate
  - Redis unavailable -> immediate alert
  
=============================================================================
PERFORMANCE CONSIDERATIONS
=============================================================================

Rate Limiting:
  - Redis latency: typically < 1ms per request
  - Recommended: Use connection pooling
  - TIP: Consider local caching for per-IP limits

Tenant Isolation:
  - TenantContext is thread-safe (uses dict)
  - No database overhead
  - TIP: Validate shop_id format upfront

Logging:
  - PII masking adds ~1-2ms per log line
  - Consider async logging for high-volume endpoints
  - TIP: Use sampling for verbose logs (DEBUG level)

Abuse Protection:
  - Input validation is CPU-bound, not I/O
  - Timeouts are async-aware (no blocking)
  - TIP: Pre-compile regex patterns if custom validation

Overall impact: < 5ms added per request for all layers combined

=============================================================================
TROUBLESHOOTING
=============================================================================

"Rate limit not working"
  - Check Redis connection: redis-cli ping
  - Check REDIS_URL environment variable
  - Look for "Failed to connect to Redis" in logs
  - Verify Redis eviction policy: CONFIG GET maxmemory-policy

"Tenant isolation not enforced"
  - Verify TenantMiddleware is added before route handlers
  - Check that endpoints use Depends(get_shop_id)
  - TenantContext must be cleared after each request
  - Test with curl: curl -H "X-Shop-ID: invalid" http://localhost:8000/api/...

"Tokens appearing in logs"
  - Verify you're using safe_log() instead of logger.info()
  - Check that PIISafeFormatter is properly configured
  - Review custom logging code for direct header logging

"Errors showing stack traces"
  - Verify exception handlers are properly registered
  - Check that HTTPException.detail is dict, not string
  - Ensure show_detail=False in ErrorResponse.internal_error()

=============================================================================
"""
