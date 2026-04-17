"""
Bots API — create, start, stop, and monitor trading bots.
Bots are wired to the execution engine and paper trading loop.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import Bot, BotStatus, Strategy, BrokerConnector

router = APIRouter()

# Running bot tasks: bot_id → asyncio.Task
_bot_tasks: dict[str, asyncio.Task] = {}


class BotCreate(BaseModel):
    name: str
    strategy_id: str
    connector_id: Optional[str] = None
    symbol: str
    exchange: str = "NSE"
    market_type: str = "equity"
    trading_mode: str = "paper"
    risk_config: Optional[dict] = None


@router.get("/")
async def list_bots(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Bot).order_by(Bot.created_at.desc()))).scalars().all()
    return [_b(b) for b in rows]


@router.post("/", status_code=201)
async def create_bot(data: BotCreate, db: AsyncSession = Depends(get_db)):
    strat = await db.get(Strategy, data.strategy_id)
    if not strat:
        raise HTTPException(404, "Strategy not found")

    # Get or use default connector
    conn_id = data.connector_id
    if not conn_id:
        result = await db.execute(
            select(BrokerConnector).where(BrokerConnector.is_default.is_(True)).limit(1)
        )
        conn = result.scalar_one_or_none()
        if not conn:
            result2 = await db.execute(select(BrokerConnector).limit(1))
            conn = result2.scalar_one_or_none()
        if conn:
            conn_id = conn.id
        else:
            # Auto-create mock connector
            conn = BrokerConnector(
                id=str(uuid.uuid4()), name="mock",
                display_name="Mock Paper",
                adapter_class="app.adapters.broker.mock_broker.MockBrokerAdapter",
                enabled=True, is_default=True,
                status="connected",
                trading_mode="paper", market_types=["equity","crypto"],
            )
            db.add(conn)
            await db.flush()
            conn_id = conn.id

    bot = Bot(
        id=str(uuid.uuid4()),
        name=data.name,
        strategy_id=data.strategy_id,
        connector_id=conn_id,
        symbol=data.symbol.upper(),
        exchange=data.exchange.upper(),
        trading_mode=data.trading_mode,
        status=BotStatus.STOPPED,
        risk_config=data.risk_config or {
            "max_daily_loss": 5000,
            "max_order_value": 50000,
            "max_open_positions": 10,
            "symbol_blacklist": [],
        },
        config={"timeframe": "15m"},
    )
    db.add(bot)
    await db.commit()
    await db.refresh(bot)
    return _b(bot)


@router.get("/{bot_id}")
async def get_bot(bot_id: str, db: AsyncSession = Depends(get_db)):
    bot = await db.get(Bot, bot_id)
    if not bot:
        raise HTTPException(404, "Bot not found")
    return _b(bot)


@router.post("/{bot_id}/start")
async def start_bot(bot_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    bot = await db.get(Bot, bot_id)
    if not bot:
        raise HTTPException(404, "Bot not found")

    strat = await db.get(Strategy, bot.strategy_id)
    if not strat:
        raise HTTPException(404, "Strategy not found")

    bot.status     = BotStatus.RUNNING
    bot.started_at = datetime.utcnow()
    await db.commit()

    # Cancel existing task if any
    old = _bot_tasks.pop(bot_id, None)
    if old and not old.done():
        old.cancel()

    # Start live paper trading loop in background
    task = asyncio.create_task(
        _run_bot_loop(bot_id, bot.symbol, strat.dsl or {})
    )
    _bot_tasks[bot_id] = task

    return {"status": "started", "bot_id": bot_id, "message": f"Bot running paper trades on {bot.symbol}"}


@router.post("/{bot_id}/stop")
async def stop_bot(bot_id: str, db: AsyncSession = Depends(get_db)):
    bot = await db.get(Bot, bot_id)
    if not bot:
        raise HTTPException(404, "Bot not found")

    task = _bot_tasks.pop(bot_id, None)
    if task and not task.done():
        task.cancel()

    bot.status     = BotStatus.STOPPED
    bot.stopped_at = datetime.utcnow()
    await db.commit()
    return {"status": "stopped", "bot_id": bot_id}


@router.post("/{bot_id}/pause")
async def pause_bot(bot_id: str, db: AsyncSession = Depends(get_db)):
    bot = await db.get(Bot, bot_id)
    if not bot:
        raise HTTPException(404, "Bot not found")
    bot.status = BotStatus.PAUSED
    await db.commit()
    return {"status": "paused"}


@router.post("/kill-all")
async def kill_all_bots(db: AsyncSession = Depends(get_db)):
    # Cancel all tasks
    for task in list(_bot_tasks.values()):
        if not task.done():
            task.cancel()
    _bot_tasks.clear()

    # Update DB
    rows = (await db.execute(select(Bot).where(Bot.status == BotStatus.RUNNING))).scalars().all()
    for b in rows:
        b.status     = BotStatus.STOPPED
        b.stopped_at = datetime.utcnow()
    await db.commit()
    return {"stopped": len(rows)}


@router.delete("/{bot_id}")
async def delete_bot(bot_id: str, db: AsyncSession = Depends(get_db)):
    bot = await db.get(Bot, bot_id)
    if not bot:
        raise HTTPException(404, "Bot not found")
    task = _bot_tasks.pop(bot_id, None)
    if task and not task.done():
        task.cancel()
    await db.delete(bot)
    await db.commit()
    return {"deleted": True}


# ── Live Bot Loop ─────────────────────────────────────────────────────────────

async def _run_bot_loop(bot_id: str, symbol: str, strategy_dsl: dict) -> None:
    """
    Continuous loop: get AI signal → execute paper trade → wait.
    Runs as an asyncio task until cancelled.
    """
    from app.services import market_stream
    from app.services.ai_strategy import get_ai_signal
    from app.core.database import AsyncSessionLocal
    import logging

    log = logging.getLogger(f"bot.{bot_id[:8]}")
    log.info("Bot loop started for %s", symbol)

    while True:
        try:
            # 1. Get latest closes
            closes = await asyncio.to_thread(market_stream.get_last_closes, symbol, 30)

            if len(closes) >= 5:
                # 2. Get AI signal (Gemini or rule-based)
                sig = await get_ai_signal(symbol, closes)
                log.info("Signal %s → %s (%.0f%% conf)",
                         symbol, sig["action"], sig["confidence"] * 100)

                # 3. Store signal in Redis so paper_trading can pick up
                from app.services.market_stream import _get_redis, AI_SIGNAL_KEY_FMT
                import json
                _get_redis().set(
                    AI_SIGNAL_KEY_FMT.format(symbol=symbol.upper()),
                    json.dumps(sig), ex=60
                )

                # 4. Execute paper trade if signal changed
                await asyncio.to_thread(_sync_execute_signals)

            # 5. Check bot is still running
            async with AsyncSessionLocal() as db:
                bot = await db.get(__import__("app.models.models", fromlist=["Bot"]).Bot, bot_id)
                if not bot or str(bot.status) not in ("running", "BotStatus.RUNNING"):
                    log.info("Bot %s stopped/paused — exiting loop", bot_id)
                    break

        except asyncio.CancelledError:
            log.info("Bot %s task cancelled", bot_id)
            break
        except Exception as e:
            log.error("Bot loop error: %s", e)

        await asyncio.sleep(10)   # Run signal check every 10 seconds


def _sync_execute_signals():
    """Sync wrapper for paper trading signal execution."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(
                __import__("app.services.paper_trading", fromlist=["execute_pending_signals_async"])
                .execute_pending_signals_async()
            )
    except Exception:
        pass


def _b(bot: Bot) -> dict:
    return {
        "id":           bot.id,
        "name":         bot.name,
        "strategy_id":  bot.strategy_id,
        "connector_id": bot.connector_id,
        "symbol":       bot.symbol,
        "exchange":     bot.exchange,
        "trading_mode": getattr(bot.trading_mode, "value", str(bot.trading_mode)) if bot.trading_mode else "paper",
        "status":       getattr(bot.status,       "value", str(bot.status)),
        "config":       bot.config,
        "risk_config":  bot.risk_config,
        "started_at":   bot.started_at.isoformat()  if bot.started_at  else None,
        "stopped_at":   bot.stopped_at.isoformat()  if bot.stopped_at  else None,
        "created_at":   bot.created_at.isoformat()  if bot.created_at  else None,
    }
