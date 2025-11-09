# README_OBSERVABILITY.md

## Overview
This pack exposes Digicloset's metrics endpoints for integration with **external Prometheus / Grafana Cloud** setups.  
It also includes **Horizontal Pod Autoscalers (HPAs)** and sample **Grafana dashboards**.

### Files
- `deploy/monitoring/metrics-service-node.yaml` — Exposes Node.js metrics on port 9100.
- `deploy/monitoring/metrics-service-python.yaml` — Exposes Python (FastAPI) metrics on port 9101.
- `deploy/monitoring/prometheus_remote_write.yaml` — Example config for Prometheus remote write to Grafana Cloud.
- `deploy/monitoring/hpa-node.yaml` and `hpa-python.yaml` — Auto-scale based on CPU usage.
- `monitoring/dashboards/` — Grafana dashboard templates for Node.js and Python inference metrics.

## Setup Instructions

1. **Instrument your apps**
   - Node.js (Express): Add `prom-client` and expose `/metrics` endpoint.
   - Python (FastAPI): Add `prometheus-fastapi-instrumentator` and expose `/metrics`.

2. **Expose metrics to external Prometheus**
   - Apply the provided `metrics-service-node.yaml` and `metrics-service-python.yaml`.
   - Replace `<EXTERNAL_PROMETHEUS_IP>` with your external endpoint or load balancer IP.

3. **Connect to Grafana Cloud / External Prometheus**
   - Edit `prometheus_remote_write.yaml` and replace `<GRAFANA_CLOUD_USER_ID>` and `<GRAFANA_CLOUD_API_KEY>`.
   - Upload or reference this config in your external Prometheus.

4. **Import Dashboards**
   - In Grafana, go to **Dashboards → Import**.
   - Upload `node_dashboard.json` and `python_dashboard.json`.

5. **Enable Autoscaling**
   ```bash
   kubectl apply -f deploy/monitoring/hpa-node.yaml
   kubectl apply -f deploy/monitoring/hpa-python.yaml
   ```

6. **Validate**
   ```bash
   kubectl get hpa
   kubectl top pods
   ```

---
💡 *This configuration allows seamless integration with Grafana Cloud or any managed Prometheus/Grafana environment, without deploying them locally.*