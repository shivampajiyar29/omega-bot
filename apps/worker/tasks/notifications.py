"""
Celery notification tasks — send alerts through configured channels.
"""
from app.worker.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="app.worker.tasks.notifications.send_notification")
def send_notification(message: str, level: str = "info", title: str = None):
    """Send a notification through all enabled channels."""
    import asyncio
    from app.services.notifications import notifications

    async def _send():
        await notifications.notify(message, level=level, title=title)

    asyncio.get_event_loop().run_until_complete(_send())
    logger.info(f"Notification sent [{level}]: {title or message[:50]}")


@celery_app.task(name="app.worker.tasks.notifications.notify_order_filled")
def notify_order_filled(symbol: str, side: str, qty: float, price: float, pnl: float = None):
    import asyncio
    from app.services.notifications import notifications

    async def _send():
        await notifications.notify_order_filled(symbol, side, qty, price, pnl)

    asyncio.get_event_loop().run_until_complete(_send())


@celery_app.task(name="app.worker.tasks.notifications.notify_risk_event")
def notify_risk_event(event_type: str, message: str):
    import asyncio
    from app.services.notifications import notifications

    async def _send():
        await notifications.notify_risk_event(event_type, message)

    asyncio.get_event_loop().run_until_complete(_send())


@celery_app.task(name="app.worker.tasks.notifications.notify_kill_switch")
def notify_kill_switch(bots_stopped: int):
    import asyncio
    from app.services.notifications import notifications

    async def _send():
        await notifications.notify_kill_switch(bots_stopped)

    asyncio.get_event_loop().run_until_complete(_send())
