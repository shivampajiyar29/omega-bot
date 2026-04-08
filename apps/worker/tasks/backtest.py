"""
Celery tasks for running backtests asynchronously.
"""
from app.worker.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.worker.tasks.backtest.run_backtest")
def run_backtest(self, backtest_id: str):
    """
    Run a backtest in the background.
    Called when a new Backtest record is created via the API.
    """
    import asyncio
    from app.api.v1.endpoints.backtests import _run_backtest_task, BacktestCreate
    from app.core.database import AsyncSessionLocal
    from app.models.models import Backtest

    async def _run():
        async with AsyncSessionLocal() as db:
            bt = await db.get(Backtest, backtest_id)
            if not bt:
                logger.error(f"Backtest {backtest_id} not found")
                return

            strat = await db.get(__import__("app.models.models", fromlist=["Strategy"]).Strategy, bt.strategy_id)
            if not strat:
                logger.error(f"Strategy {bt.strategy_id} not found")
                return

            data = BacktestCreate(
                strategy_id=bt.strategy_id,
                symbol=bt.symbol,
                exchange=bt.exchange,
                timeframe=bt.timeframe,
                start_date=bt.start_date.isoformat(),
                end_date=bt.end_date.isoformat(),
                initial_capital=bt.initial_capital,
                commission_pct=bt.commission_pct,
                slippage_pct=bt.slippage_pct,
                params=bt.params or {},
            )
            await _run_backtest_task(backtest_id, strat.dsl, data)
            logger.info(f"Backtest {backtest_id} completed")

    asyncio.get_event_loop().run_until_complete(_run())
    return {"backtest_id": backtest_id, "status": "completed"}


@celery_app.task(name="app.worker.tasks.backtest.cancel_backtest")
def cancel_backtest(backtest_id: str):
    """Cancel a running backtest."""
    logger.info(f"Cancelling backtest {backtest_id}")
    # TODO: implement cancellation via task revocation
    return {"cancelled": True}
