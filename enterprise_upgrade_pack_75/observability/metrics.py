from prometheus_client import Counter, Histogram

requests_total = Counter("requests_total", "Total HTTP Requests")
latency = Histogram("request_latency_seconds", "Request latency")

def record_request():
    requests_total.inc()

def record_latency(value):
    latency.observe(value)
