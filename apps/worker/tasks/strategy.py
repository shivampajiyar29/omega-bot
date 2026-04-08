"""
Celery tasks for strategy signal processing.
"""
from app.worker.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="app.worker.tasks.strategy.evaluate_signal")
def evaluate_signal(bot_id: str):
    """
    Trigger a one-off strategy signal evaluation for a bot.
    Used when a new bar arrives and we need to check for entry/exit.
    """
    import asyncio
    from app.execution.bot_manager import bot_manager

    stats = bot_manager.get_status(bot_id)
    if not stats:
        logger.debug(f"Bot {bot_id} not running, skipping signal evaluation")
        return {"skipped": True}

    logger.debug(f"Signal evaluation triggered for bot {bot_id}")
    return {"bot_id": bot_id, "status": stats.get("status")}


@celery_app.task(name="app.worker.tasks.strategy.process_webhook_signal")
def process_webhook_signal(signal_data: dict):
    """
    Process an incoming webhook signal (e.g. from TradingView).
    Routes to the appropriate bot or places a manual order.
    """
    import asyncio
    from app.execution.bot_manager import bot_manager

    symbol = signal_data.get("symbol", "")
    action = signal_data.get("action", "")  # buy | sell | exit
    price  = signal_data.get("price")
    qty    = signal_data.get("quantity", 1.0)

    logger.info(f"Webhook signal: {action.upper()} {symbol} @ {price} qty={qty}")

    # TODO: route to active bot on this symbol, or place a manual order
    return {"processed": True, "symbol": symbol, "action": action}
