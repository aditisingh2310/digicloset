# README_CLOUD.md

## Overview
This pack introduces **Cloud Cost Optimization & Auto-Scaling** for Digicloset.

### Features
- **Horizontal Pod Autoscaling (HPA)** — Automatically scales pods based on CPU & memory usage.
- **Resource Quotas** — Prevents excessive resource usage per namespace.
- **Cost Exporter** — Emits simulated cost metrics for Prometheus/Grafana (no real billing required).
- **Grafana Dashboard** — Visualizes estimated cost and utilization.

### How to Deploy
```bash
kubectl apply -f deploy/autoscale/hpa-backend.yaml
kubectl apply -f deploy/autoscale/hpa-frontend.yaml
kubectl apply -f deploy/autoscale/resource-quota.yaml
kubectl apply -f monitoring/cost-exporter/deployment.yaml
kubectl apply -f monitoring/cost-exporter/service.yaml
```

### Grafana Setup
1. Import the dashboard from `monitoring/dashboards/cost_dashboard.json`.
2. Ensure Prometheus is scraping `cost-exporter:9100/metrics`.
3. View service-wise cost and utilization trends.

### Sample Metrics (Simulated)
```
cost_cpu_usd{service="backend"} 0.15
cost_memory_usd{service="frontend"} 0.09
```
These metrics are based on simulated rates (`COST_CPU_RATE`, `COST_MEM_RATE`) configurable in the exporter.

---
✅ *This pack enables cost awareness, auto-scaling, and efficient cloud utilization for Digicloset.*