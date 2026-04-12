"""
Backtester API endpoints.
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import uuid

from app.core.database import get_db
from app.models.models import Backtest, Strategy

router = APIRouter()


class BacktestCreate(BaseModel):
    strategy_id: str
    symbol: str
    exchange: str
    timeframe: str = "15m"
    start_date: str   # ISO format
    end_date: str
    initial_capital: float = 100_000.0
    commission_pct: float = 0.03
    slippage_pct: float = 0.01
    params: Optional[dict] = None
    name: Optional[str] = None


@router.get("/", response_model=List[dict])
async def list_backtests(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Backtest).order_by(Backtest.created_at.desc()).limit(50)
    )
    backtests = result.scalars().all()
    return [_bt_to_dict(bt) for bt in backtests]


@router.post("/", response_model=dict)
async def create_backtest(
    data: BacktestCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Validate strategy exists
    strat = await db.get(Strategy, data.strategy_id)
    if not strat:
        raise HTTPException(status_code=404, detail="Strategy not found")

    bt = Backtest(
        id=str(uuid.uuid4()),
        strategy_id=data.strategy_id,
        name=data.name or f"{strat.name} — {data.symbol} {data.timeframe}",
        symbol=data.symbol,
        exchange=data.exchange,
        start_date=datetime.fromisoformat(data.start_date),
        end_date=datetime.fromisoformat(data.end_date),
        timeframe=data.timeframe,
        initial_capital=data.initial_capital,
        commission_pct=data.commission_pct,
        slippage_pct=data.slippage_pct,
        params=data.params or {},
        status="pending",
    )
    db.add(bt)
    await db.commit()
    await db.refresh(bt)

    # Queue the actual backtest run
    background_tasks.add_task(_run_backtest_task, bt.id, strat.dsl, data)

    return _bt_to_dict(bt)


@router.get("/{backtest_id}", response_model=dict)
async def get_backtest(backtest_id: str, db: AsyncSession = Depends(get_db)):
    bt = await db.get(Backtest, backtest_id)
    if not bt:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return _bt_to_dict(bt)


@router.delete("/{backtest_id}")
async def delete_backtest(backtest_id: str, db: AsyncSession = Depends(get_db)):
    bt = await db.get(Backtest, backtest_id)
    if not bt:
        raise HTTPException(status_code=404, detail="Backtest not found")
    await db.delete(bt)
    await db.commit()
    return {"deleted": True}


# ─── Background task ─────────────────────────────────────────────────────────

async def _run_backtest_task(bt_id: str, strategy_dsl: dict, data: BacktestCreate):
    """
    Run the actual backtest. Called in background.
    In production this would be a Celery task.
    """
    from app.core.database import AsyncSessionLocal
    from app.adapters.marketdata.mock_data import MockMarketDataAdapter
    from app.backtester.engine import BacktestEngine, Bar
    from app.backtester.evaluator import DSLEvaluator

    async with AsyncSessionLocal() as db:
        bt = await db.get(Backtest, bt_id)
        if not bt:
            return

        bt.status = "running"
        bt.started_at = datetime.utcnow()
        await db.commit()

        try:
            # Fetch historical data
            adapter = MockMarketDataAdapter()
            await adapter.connect()
            ohlcv = await adapter.get_historical_ohlcv(
                symbol=data.symbol,
                exchange=data.exchange,
                timeframe=data.timeframe,
                start=datetime.fromisoformat(data.start_date),
                end=datetime.fromisoformat(data.end_date),
            )

            bars = [
                Bar(
                    timestamp=o.timestamp, open=o.open, high=o.high,
                    low=o.low, close=o.close, volume=o.volume,
                )
                for o in ohlcv
            ]

            # Build strategy signal function
            evaluator = DSLEvaluator(strategy_dsl)
            signal_fn = evaluator.get_signal_fn()

            # Run engine
            engine = BacktestEngine(
                bars=bars,
                strategy_fn=signal_fn,
                symbol=data.symbol,
                timeframe=data.timeframe,
                initial_capital=data.initial_capital,
                commission_pct=data.commission_pct,
                slippage_pct=data.slippage_pct,
                params=data.params or {},
            )
            results = engine.run()

            bt.status = "completed"
            bt.results = {
                k: v for k, v in results.__dict__.items()
                if k not in ("equity_curve", "trade_log", "monthly_returns")
            }
            bt.equity_curve = results.equity_curve
            bt.trade_log = results.trade_log
            bt.completed_at = datetime.utcnow()

        except Exception as e:
            bt.status = "failed"
            bt.error_message = str(e)
            import traceback
            traceback.print_exc()

        await db.commit()


def _bt_to_dict(bt: Backtest) -> dict:
    return {
        "id": bt.id,
        "strategy_id": bt.strategy_id,
        "name": bt.name,
        "symbol": bt.symbol,
        "exchange": bt.exchange,
        "start_date": bt.start_date.isoformat() if bt.start_date else None,
        "end_date": bt.end_date.isoformat() if bt.end_date else None,
        "timeframe": bt.timeframe,
        "initial_capital": bt.initial_capital,
        "commission_pct": bt.commission_pct,
        "slippage_pct": bt.slippage_pct,
        "status": bt.status,
        "results": bt.results,
        "equity_curve": bt.equity_curve,
        "trade_log": bt.trade_log,
        "error_message": bt.error_message,
        "created_at": bt.created_at.isoformat() if bt.created_at else None,
        "completed_at": bt.completed_at.isoformat() if bt.completed_at else None,
    }
