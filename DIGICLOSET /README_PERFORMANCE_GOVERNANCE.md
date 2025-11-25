# Performance & Governance Automation Setup

## 1. Performance Testing (Locust)
Run with:
```bash
pip install -r performance/requirements.txt
locust -f performance/loadtest/locustfile.py --host https://your-api-url.com
```

## 2. IAM Integration
Edit `iam_integration_template.yaml` to match your Okta / Azure AD credentials.
Apply in Kubernetes via:
```bash
kubectl apply -f governance/iam_integration_template.yaml
```

## 3. Audit Streaming
Configure `audit_streaming_config.yaml` to send security logs to your SIEM (Datadog, Splunk, etc).

## 4. Validation
- Target: 1000 req/s sustained
- Error Rate: <1%
- Governance: Role-based auth via IAM
