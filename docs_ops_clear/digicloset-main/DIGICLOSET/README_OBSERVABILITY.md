# README_OBSERVABILITY.md

## Overview
This pack adds **Observability, Alerts & SLA Monitoring** to Digicloset.

### Components
- **OpenTelemetry Collector**: Centralized telemetry pipeline for metrics, logs, and traces.
- **Prometheus Alert Rules**: SLA, error-rate, and latency alerts.
- **Alertmanager (Slack)**: Sends alert notifications to Slack.
- **Grafana Dashboard**: SLA & reliability overview dashboard.

### Setup Instructions

1. **Apply OpenTelemetry Collector**
```bash
kubectl apply -f monitoring/otel/otel-collector.yaml
```

2. **Deploy Alert Rules**
```bash
kubectl apply -f monitoring/alerts/prometheus-rules.yaml
```

3. **Configure Alertmanager**
Replace `YOUR/SLACK/WEBHOOK` with your real Slack webhook URL, then apply:
```bash
kubectl apply -f monitoring/alerts/alertmanager-config.yaml
```

4. **Import Dashboard**
Import `monitoring/dashboards/sla_dashboard.json` into Grafana.

### Example Alerts
- HighErrorRate — 5xx > 3% for 5m
- LatencySpike — p95 latency > 1s for 5m
- UptimeSLA — uptime < 99.5% over 24h
- PodCrashLoop — restarts > 3 in 10m

---
✅ *This pack ensures enterprise-grade reliability visibility and proactive alerting.*