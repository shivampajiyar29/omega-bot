"""Celery application configuration."""

from datetime import timedelta

from celery import Celery

from app.core.config import settings


celery_app = Celery(
    "omegabot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "omegabot-fetch-market-data": {
            "task": "omegabot.fetch_market_data",
            "schedule": timedelta(seconds=2),
        },
        "omegabot-run-ai-strategy": {
            "task": "omegabot.run_ai_strategy",
            "schedule": timedelta(seconds=5),
        },
        "omegabot-execute-trades": {
            "task": "omegabot.execute_trades",
            "schedule": timedelta(seconds=5),
        },
    },
)

celery_app.autodiscover_tasks(["app.worker"])
import app.worker.tasks  # noqa: E402,F401 — register task modules

