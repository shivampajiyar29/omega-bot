"""
Bots API — manage trading bot instances.
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
import uuid

from app.core.database import get_db
from app.models.models import Bot, BotStatus, TradingMode

router = APIRouter()


class BotCreate(BaseModel):
    name: str
    strategy_id: str
    connector_id: str
    symbol: str
    exchange: str
    market_type: str = "equity"
    trading_mode: str = "paper"
    config: Optional[dict] = None
    risk_config: Optional[dict] = None


class BotUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[dict] = None
    risk_config: Optional[dict] = None
    trading_mode: Optional[str] = None


@router.get("/", response_model=List[dict])
async def list_bots(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Bot).order_by(Bot.created_at.desc()))
    return [_b(bot) for bot in result.scalars().all()]


@router.post("/", response_model=dict, status_code=201)
async def create_bot(data: BotCreate, db: AsyncSession = Depends(get_db)):
    bot = Bot(
        id=str(uuid.uuid4()),
        name=data.name,
        strategy_id=data.strategy_id,
        connector_id=data.connector_id,
        symbol=data.symbol,
        exchange=data.exchange,
        market_type=data.market_type,
        trading_mode=data.trading_mode,
        status=BotStatus.STOPPED,
        config=data.config or {},
        risk_config=data.risk_config or {},
    )
    db.add(bot)
    await db.commit()
    await db.refresh(bot)
    return _b(bot)


@router.get("/{bot_id}", response_model=dict)
async def get_bot(bot_id: str, db: AsyncSession = Depends(get_db)):
    bot = await db.get(Bot, bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return _b(bot)


@router.patch("/{bot_id}", response_model=dict)
async def update_bot(bot_id: str, data: BotUpdate, db: AsyncSession = Depends(get_db)):
    bot = await db.get(Bot, bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    if data.name:
        bot.name = data.name
    if data.config is not None:
        bot.config = data.config
    if data.risk_config is not None:
        bot.risk_config = data.risk_config
    if data.trading_mode:
        bot.trading_mode = data.trading_mode
    await db.commit()
    await db.refresh(bot)
    return _b(bot)


@router.delete("/{bot_id}")
async def delete_bot(bot_id: str, db: AsyncSession = Depends(get_db)):
    bot = await db.get(Bot, bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    if bot.status == BotStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Stop the bot before deleting")
    await db.delete(bot)
    await db.commit()
    return {"deleted": True}


@router.post("/{bot_id}/start", response_model=dict)
async def start_bot(bot_id: str, db: AsyncSession = Depends(get_db)):
    bot = await db.get(Bot, bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    if bot.status == BotStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Bot is already running")
    bot.status = BotStatus.RUNNING
    bot.started_at = datetime.utcnow()
    bot.stopped_at = None
    await db.commit()
    # TODO: dispatch to worker/execution engine
    return {"status": "started", "bot": _b(bot)}


@router.post("/{bot_id}/stop", response_model=dict)
async def stop_bot(bot_id: str, db: AsyncSession = Depends(get_db)):
    bot = await db.get(Bot, bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    bot.status = BotStatus.STOPPED
    bot.stopped_at = datetime.utcnow()
    await db.commit()
    return {"status": "stopped", "bot": _b(bot)}


@router.post("/{bot_id}/pause", response_model=dict)
async def pause_bot(bot_id: str, db: AsyncSession = Depends(get_db)):
    bot = await db.get(Bot, bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    bot.status = BotStatus.PAUSED
    await db.commit()
    return {"status": "paused", "bot": _b(bot)}


@router.post("/kill-all", response_model=dict)
async def kill_all_bots(db: AsyncSession = Depends(get_db)):
    """Emergency: stop all running and paused bots immediately."""
    result = await db.execute(
        select(Bot).where(Bot.status.in_([BotStatus.RUNNING, BotStatus.PAUSED]))
    )
    bots = result.scalars().all()
    now = datetime.utcnow()
    for bot in bots:
        bot.status = BotStatus.STOPPED
        bot.stopped_at = now
    await db.commit()
    return {"killed": len(bots), "message": f"Stopped {len(bots)} bots"}


def _b(bot: Bot) -> dict:
    return {
        "id": bot.id,
        "name": bot.name,
        "strategy_id": bot.strategy_id,
        "connector_id": bot.connector_id,
        "symbol": bot.symbol,
        "exchange": bot.exchange,
        "market_type": bot.market_type,
        "trading_mode": bot.trading_mode,
        "status": bot.status,
        "config": bot.config or {},
        "risk_config": bot.risk_config or {},
        "started_at": bot.started_at.isoformat() if bot.started_at else None,
        "stopped_at": bot.stopped_at.isoformat() if bot.stopped_at else None,
        "created_at": bot.created_at.isoformat() if bot.created_at else None,
    }
