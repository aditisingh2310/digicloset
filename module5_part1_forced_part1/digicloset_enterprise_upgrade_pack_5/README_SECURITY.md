# README_SECURITY.md

## Overview
This pack introduces enterprise-grade **Security & Compliance** features.

### Components
- **RBAC**: Role and RoleBinding for Kubernetes least-privilege access.
- **API Key Management**: Middleware for Supabase-backed key validation.
- **Rate Limiting**: Protects APIs from abuse (per key/IP).
- **Audit Logging**: Structured, tamper-evident JSON logs.

### Supabase Table Schema
```sql
create table api_keys (
  id uuid primary key default uuid_generate_v4(),
  key text unique not null,
  owner_id uuid references profiles(id),
  created_at timestamptz default now(),
  revoked boolean default false
);
```

### Key Rotation
- To revoke: `update api_keys set revoked = true where key = '<key>';`
- To rotate: insert a new key and update clients.

### Integration (Node.js)
```js
import express from 'express';
import { apiKeyMiddleware } from './config/security/api_key_middleware.js';
import { apiRateLimiter } from './config/security/rate_limit.js';

const app = express();
app.use(apiRateLimiter);
app.use(apiKeyMiddleware);
```

### Integration (Python / FastAPI)
```python
from fastapi import FastAPI, Depends
from config.security.api_key_middleware import api_key_dependency
from config.security.rate_limit import setup_rate_limit

app = FastAPI()
setup_rate_limit(app)

@app.get("/secure", dependencies=[Depends(api_key_dependency)])
async def secure_route():
    return {"message": "Access granted"}
```

### Audit Logging
All access attempts are logged to `AUDIT_LOG_PATH` (default: `./audit.log`).
Logs can be shipped to Grafana Loki or AWS CloudWatch.

---
✅ *This pack ensures Digicloset meets enterprise-grade authentication, compliance, and auditability standards.*