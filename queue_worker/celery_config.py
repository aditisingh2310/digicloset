"""
Celery Configuration

Production-ready Celery setup with:
- Redis broker
- Result backend
- Task routing
- Retry policies
- Monitoring
"""

import os
from kombu import Exchange, Queue
from datetime import timedelta

# ============================================================
# BROKER & RESULT BACKEND
# ============================================================

CELERY_BROKER_URL = os.getenv(
    "CELERY_BROKER_URL",
    "redis://:@localhost:6379/0"
)

CELERY_RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND",
    "redis://:@localhost:6379/1"
)

# ============================================================
# TASK CONFIGURATION
# ============================================================

CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"
CELERY_ENABLE_UTC = True

# Task time limits
CELERY_TASK_TIME_LIMIT = 15 * 60  # 15 minutes hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 14 * 60  # 14 minutes soft limit

# Result retention time
CELERY_RESULT_EXPIRES = 24 * 60 * 60  # 24 hours

# ============================================================
# TASK ROUTING
# ============================================================

default_exchange = Exchange('tasks', type='direct')
default_queue = Queue('default', exchange=default_exchange, routing_key='default')

tryon_exchange = Exchange('tryon', type='direct')
tryon_queue = Queue(
    'tryon',
    exchange=tryon_exchange,
    routing_key='tryon.priority'
)

CELERY_QUEUES = (
    default_queue,
    tryon_queue,
)

CELERY_ROUTES = {
    'queue_worker.tryon_tasks.generate_tryon_task': {
        'queue': 'tryon',
        'routing_key': 'tryon.priority',
        'exchange': 'tryon'
    },
    'queue_worker.tryon_tasks.cleanup_old_jobs': {
        'queue': 'default'
    },
    'queue_worker.tryon_tasks.reset_monthly_limits': {
        'queue': 'default'
    }
}

# ============================================================
# TASK SCHEDULES
# ============================================================

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Cleanup old jobs daily at 2 AM UTC
    'cleanup-old-jobs': {
        'task': 'queue_worker.tryon_tasks.cleanup_old_jobs',
        'schedule': crontab(hour=2, minute=0),
        'kwargs': {'days': 30}
    },
    
    # Reset monthly limits on 1st day of each month at 00:00 UTC
    'reset-monthly-limits': {
        'task': 'queue_worker.tryon_tasks.reset_monthly_limits',
        'schedule': crontab(day_of_month=1, hour=0, minute=0),
    },
}

# ============================================================
# RETRY POLICY
# ============================================================

CELERY_TASK_AUTORETRY_FOR = (Exception,)
CELERY_TASK_MAX_RETRIES = 3
CELERY_TASK_DEFAULT_RETRY_DELAY = 60  # seconds

# ============================================================
# ERROR HANDLING
# ============================================================

# Log task events for monitoring
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_SEND_SENT_EVENT = True
CELERY_SEND_TASK_ERROR_EMAILS = False  # Use alerting instead

# ============================================================
# PERFORMANCE TUNING
# ============================================================

# Worker prefetch multiplier
CELERY_WORKER_PREFETCH_MULTIPLIER = 4

# Disable connection pooling for better control
CELERY_BROKER_POOL_LIMIT = 0

# Redis connection pooling
CELERY_REDIS_MAX_CONNECTIONS = 50

# ============================================================
# WORKER CONFIGURATION
# ============================================================

# Concurrency settings
# Use these with: celery -A queue_worker.app worker -c 4 -Q tryon,default

CELERY_WORKER_CONCURRENCY = int(os.getenv("CELERY_WORKER_CONCURRENCY", "4"))

# Task time limits
CELERY_WORKER_TASK_TIME_LIMIT = 15 * 60  # Hard kill after 15 minutes
CELERY_WORKER_TASK_SOFT_TIME_LIMIT = 14 * 60  # Warning after 14 minutes

# ============================================================
# MONITORING & OBSERVABILITY
# ============================================================

# Sentry integration (if configured)
if os.getenv("SENTRY_DSN"):
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        integrations=[CeleryIntegration()],
        environment=os.getenv("ENVIRONMENT", "development")
    )

# Prometheus metrics
CELERY_PROMETHEUS_ENABLED = os.getenv("CELERY_PROMETHEUS_ENABLED", "false").lower() == "true"

# ============================================================
# DEPLOYMENT NOTES
# ============================================================

"""
Production Worker Deployment:

1. Redis Setup:
   docker run -d -p 6379:6379 redis:latest

2. Celery Worker:
   celery -A queue_worker.app worker \
     --loglevel=INFO \
     --concurrency=4 \
     -Q tryon,default \
     --prefetch-multiplier=4 \
     --time-limit=900 \
     --soft-time-limit=840

3. Celery Beat (Schedules):
   celery -A queue_worker.app beat \
     --loglevel=INFO

4. Monitoring:
   celery -A queue_worker.app events
   celery -A queue_worker.app inspect active

5. Configuration Environment Variables:
   - CELERY_BROKER_URL: Redis connection string
   - CELERY_RESULT_BACKEND: Redis result storage
   - CELERY_WORKER_CONCURRENCY: Number of worker processes
   - ENVIRONMENT: development/production/staging
   - SENTRY_DSN: Error tracking (optional)
   - CELERY_PROMETHEUS_ENABLED: Metrics (optional)
"""
