from prometheus_client import Counter, Histogram

request_counter = Counter("requests_total", "Total HTTP Requests")
latency_hist = Histogram("request_latency", "Request latency in seconds")

def record_request():
    request_counter.inc()

def record_latency(value):
    latency_hist.observe(value)
