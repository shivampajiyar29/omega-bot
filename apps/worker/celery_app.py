"""
Celery Worker — Background tasks for OmegaBot.
Handles long-running jobs: backtests, strategy signals, reconciliation.

Start with:
    celery -A app.worker worker --loglevel=info
"""
from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "omegabot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.worker.tasks.backtest",
        "app.worker.tasks.strategy",
        "app.worker.tasks.notifications",
        "app.worker.tasks.reconciliation",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.worker.tasks.backtest.*":       {"queue": "backtests"},
        "app.worker.tasks.strategy.*":       {"queue": "signals"},
        "app.worker.tasks.notifications.*":  {"queue": "notifications"},
        "app.worker.tasks.reconciliation.*": {"queue": "reconcile"},
    },
    beat_schedule={
        # Reconcile positions every 5 minutes during market hours
        "reconcile-positions": {
            "task": "app.worker.tasks.reconciliation.reconcile_positions",
            "schedule": 300.0,
        },
        # Portfolio snapshot at end of day
        "portfolio-snapshot": {
            "task": "app.worker.tasks.reconciliation.take_portfolio_snapshot",
            "schedule": 3600.0,
        },
    },
)
