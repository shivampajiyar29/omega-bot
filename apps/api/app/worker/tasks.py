"""Celery tasks: health checks, market data, AI signals, paper execution."""

import asyncio
import json
import logging

from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="omegabot.ping")
def ping() -> str:
    return "pong"


@celery_app.task(name="omegabot.fetch_market_data")
def fetch_market_data() -> None:
    """Push simulated (or external) ticks into Redis for the UI and strategies."""
    from app.services import market_stream

    try:
        market_stream.refresh_prices()
    except Exception:
        logger.exception("fetch_market_data failed")


@celery_app.task(name="omegabot.run_ai_strategy")
def run_ai_strategy() -> None:
    """Compute simple momentum signals from recent closes and store in Redis."""
    from app.core.config import settings
    from app.services.ai_strategy import generate_signal
    from app.services import market_stream

    import redis

    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    for sym in market_stream.DEFAULT_SYMBOLS:
        try:
            candles = market_stream.get_last_closes(sym, 20)
            sig = generate_signal(sym, candles)
            r.set(f"omegabot:paper:signal:{sym}", json.dumps(sig))
        except Exception:
            logger.exception("run_ai_strategy failed for %s", sym)


@celery_app.task(name="omegabot.execute_trades")
def execute_trades() -> None:
    """Execute paper orders from stored signals (async DB session inside)."""
    from app.services.paper_trading import execute_pending_signals_async

    try:
        asyncio.run(execute_pending_signals_async())
    except Exception:
        logger.exception("execute_trades failed")
