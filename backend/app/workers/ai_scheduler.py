import time
from app.workers.ai_jobs import bulk_reanalyze

def daily_scan(fetch_products_fn):
    while True:
        products = fetch_products_fn()
        bulk_reanalyze(products)
        time.sleep(86400)  # 24 hours
