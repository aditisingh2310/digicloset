# README_RESILIENCE.md

## Overview
This pack introduces **advanced resilience and reliability** mechanisms for Digicloset, including:
- Circuit breakers with Prometheus metrics
- Retry logic with exponential backoff
- Graceful shutdown handlers
- Kubernetes liveness/readiness probes
- Restart and backoff policies

### ⚙️ Environment Variables
| Variable | Description | Default |
|-----------|--------------|----------|
| RETRY_COUNT | Number of retries before failure | 3 |
| BACKOFF_MS | Delay (ms) between retries | 1000 |
| CIRCUIT_TIMEOUT_SEC | Duration (s) circuit stays open after failure | 60 |

### 🧠 Node.js Integration
```js
import { resilientRequest } from './config/resilience/node_resilience.js';
import { setupGracefulShutdown } from './config/resilience/graceful_shutdown.js';
import express from 'express';

const app = express();
const server = app.listen(3000);
setupGracefulShutdown(server);
```

### 🧩 Python Integration
```python
from config.resilience.python_resilience import resilient_request
from config.resilience.graceful_shutdown import setup_graceful_shutdown

# Example FastAPI
from fastapi import FastAPI
app = FastAPI()

@app.get("/health/live")
def live(): return {"status": "ok"}

@app.get("/health/ready")
def ready(): return {"status": "ok"}
```

### 🩺 Kubernetes Setup
Apply probes and policies:
```bash
kubectl apply -f deploy/health/node_health.yaml
kubectl apply -f deploy/health/python_health.yaml
kubectl apply -f deploy/health/pod_policies.yaml
```

---
💡 *This pack ensures your system can handle transient failures, auto-recover, and degrade gracefully under stress.*