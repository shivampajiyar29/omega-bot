"""
Reconciliation tasks — keep local state in sync with broker.
"""
from app.worker.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="app.worker.tasks.reconciliation.reconcile_positions")
def reconcile_positions():
    """
    Compare local position records with broker's actual positions.
    Flags discrepancies and updates stale records.
    Runs every 5 minutes via Celery beat.
    """
    import asyncio

    async def _run():
        from app.core.database import AsyncSessionLocal
        from app.models.models import BrokerConnector, Position, ConnectorStatus

        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            # Get default active connector
            result = await db.execute(
                select(BrokerConnector).where(
                    BrokerConnector.is_default == True,
                    BrokerConnector.status == ConnectorStatus.CONNECTED,
                )
            )
            connector = result.scalar_one_or_none()
            if not connector:
                logger.debug("No active connector for reconciliation")
                return

            # For mock broker, nothing to reconcile
            if connector.name == "mock":
                return

            # TODO: for real brokers:
            # 1. Get broker positions via adapter
            # 2. Compare with local Position records
            # 3. Update mismatched records
            # 4. Create RiskEvent for large discrepancies
            logger.info(f"Reconciliation complete for connector: {connector.name}")

    asyncio.get_event_loop().run_until_complete(_run())


@celery_app.task(name="app.worker.tasks.reconciliation.take_portfolio_snapshot")
def take_portfolio_snapshot():
    """
    Take a daily portfolio value snapshot.
    Runs every hour via Celery beat.
    """
    import asyncio
    from datetime import datetime

    async def _run():
        from app.core.database import AsyncSessionLocal
        from app.models.models import PortfolioSnapshot, TradingMode

        async with AsyncSessionLocal() as db:
            # TODO: compute real portfolio value from positions + cash
            snapshot = PortfolioSnapshot(
                date=datetime.utcnow(),
                total_value=1_000_000.0,  # placeholder
                cash=700_000.0,
                positions_value=300_000.0,
                daily_pnl=0.0,
                total_pnl=0.0,
                trading_mode=TradingMode.PAPER,
            )
            db.add(snapshot)
            await db.commit()
            logger.info("Portfolio snapshot taken")

    asyncio.get_event_loop().run_until_complete(_run())
