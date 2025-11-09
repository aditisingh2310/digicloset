import json, time
def generate(control, status):
    entry = {"control": control, "status": status, "timestamp": time.time()}
    print(json.dumps(entry))
