# app/celery_app.py
# Celery configuration
# - Celery app instance
# - Broker/backend configuration (Redis)
# - Task discovery

import os
from celery import Celery

# Get Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

# Create Celery app instance
celery_app = Celery(
    "worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["app.tasks"]  # Auto-discover tasks
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task routing
    task_routes={
        "app.tasks.*": {"queue": "celery"}
    },
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_persistent=False,
    
    # Task execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Concurrency (can be overridden via env)
    worker_concurrency=int(os.getenv("CELERY_CONCURRENCY", "4")),
)

# Export celery instance
__all__ = ["celery_app"]
