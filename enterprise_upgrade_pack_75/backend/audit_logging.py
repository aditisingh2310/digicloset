import json, time

def audit_log(event_type, user, metadata=None):
    entry = {
        "ts": time.time(),
        "event": event_type,
        "user": user,
        "metadata": metadata or {}
    }
    print(json.dumps(entry))
