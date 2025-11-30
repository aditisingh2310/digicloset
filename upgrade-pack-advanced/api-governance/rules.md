# API Governance Rules
- All endpoints must include versioning: /v1/…
- Required headers: X-Request-ID, X-Correlation-ID
- Use standard error model with consistent structure
- PATCH for partial updates; PUT for full replacement
