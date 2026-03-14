"""
Queue Worker Application

Celery app initialization with:
- Redis broker connection
- Task discovery
- Error handling
- Health checks
"""

import logging
import os
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure

logger = logging.getLogger(__name__)

# ============================================================
# CELERY APP INITIALIZATION
# ============================================================

app = Celery('queue_worker')

# Load configuration
app.config_from_object('queue_worker.celery_config')

# Auto-discover tasks from modules
app.autodiscover_tasks(['queue_worker'])

# ============================================================
# SIGNAL HANDLERS
# ============================================================

@task_prerun.connect
def on_task_prerun(sender=None, task_id=None, task=None, **kwargs):
    """Log when task starts"""
    logger.info(f"Task {task.name} [{task_id}] started")


@task_postrun.connect
def on_task_postrun(sender=None, task_id=None, result=None, **kwargs):
    """Log when task completes"""
    logger.info(f"Task completed with result: {result}")


@task_failure.connect
def on_task_failure(sender=None, task_id=None, exception=None, **kwargs):
    """Log task failures"""
    logger.error(f"Task failed [{task_id}]: {exception}")


# ============================================================
# HEALTH CHECK ENDPOINTS
# ============================================================

def check_celery_health() -> dict:
    """Check Celery worker and broker health"""
    try:
        # Check if workers are alive
        inspect = app.control.inspect()
        stats = inspect.stats()
        
        if not stats:
            return {
                "status": "unhealthy",
                "message": "No workers connected",
                "workers": 0
            }
        
        workers = len(stats)
        active_tasks = sum(
            len(inspect.active().get(w, []))
            for w in stats.keys()
        )
        
        return {
            "status": "healthy",
            "workers": workers,
            "active_tasks": active_tasks,
            "message": f"{workers} workers active"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": str(e)
        }


# ============================================================
# TASK STATUS HELPER
# ============================================================

def get_task_status(task_id: str) -> dict:
    """Get status of a specific task"""
    from celery.result import AsyncResult
    
    result = AsyncResult(task_id, app=app)
    
    return {
        "task_id": task_id,
        "status": result.state,
        "result": result.result if result.successful() else None,
        "error": str(result.info) if result.failed() else None
    }


# ============================================================
# MONITORING & LOGGING
# ============================================================

def setup_logging():
    """Configure logging for Celery tasks"""
    
    logging.basicConfig(
        level=os.getenv("CELERY_LOG_LEVEL", "INFO"),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set Celery logger
    celery_logger = logging.getLogger('celery')
    celery_logger.setLevel(os.getenv("CELERY_LOG_LEVEL", "INFO"))


setup_logging()


# ============================================================
# EXPORTED ITEMS
# ============================================================

__all__ = [
    'app',
    'check_celery_health',
    'get_task_status',
    'setup_logging'
]

if __name__ == '__main__':
    app.start()
