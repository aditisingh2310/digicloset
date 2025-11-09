import requests
def check():
    try:
        r = requests.get("https://example.com/health")
        print("OK" if r.status_code == 200 else "FAIL")
    except:
        print("FAIL")
