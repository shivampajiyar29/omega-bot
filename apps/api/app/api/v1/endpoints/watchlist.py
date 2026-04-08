"""
Watchlist API — symbol watchlist management.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import uuid

from app.core.database import get_db
from app.models.models import Watchlist, WatchlistSymbol

router = APIRouter()


class SymbolAdd(BaseModel):
    symbol: str
    exchange: str
    market_type: str = "equity"


@router.get("/", response_model=dict)
async def get_default_watchlist(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Watchlist).where(Watchlist.is_default == True).limit(1))
    wl = result.scalar_one_or_none()

    if not wl:
        # Return mock data for first-time users
        return {
            "id": "default",
            "name": "My Watchlist",
            "symbols": [
                {"symbol": "RELIANCE",   "exchange": "NSE",     "market_type": "equity"},
                {"symbol": "TCS",        "exchange": "NSE",     "market_type": "equity"},
                {"symbol": "INFY",       "exchange": "NSE",     "market_type": "equity"},
                {"symbol": "HDFC",       "exchange": "NSE",     "market_type": "equity"},
                {"symbol": "BAJFINANCE", "exchange": "NSE",     "market_type": "equity"},
                {"symbol": "BTCUSDT",    "exchange": "BINANCE", "market_type": "crypto"},
                {"symbol": "NIFTY50",    "exchange": "NSE",     "market_type": "index"},
            ],
        }

    syms_result = await db.execute(
        select(WatchlistSymbol).where(WatchlistSymbol.watchlist_id == wl.id)
        .order_by(WatchlistSymbol.added_at)
    )
    return {
        "id":      wl.id,
        "name":    wl.name,
        "symbols": [
            {"symbol": s.symbol, "exchange": s.exchange, "market_type": s.market_type}
            for s in syms_result.scalars().all()
        ],
    }


@router.get("/all", response_model=List[dict])
async def list_watchlists(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Watchlist).order_by(Watchlist.created_at))
    return [{"id": w.id, "name": w.name, "is_default": w.is_default} for w in result.scalars().all()]


@router.post("/symbols", response_model=dict, status_code=201)
async def add_symbol(data: SymbolAdd, db: AsyncSession = Depends(get_db)):
    # Ensure default watchlist exists
    result = await db.execute(select(Watchlist).where(Watchlist.is_default == True).limit(1))
    wl = result.scalar_one_or_none()
    if not wl:
        wl = Watchlist(id=str(uuid.uuid4()), name="My Watchlist", is_default=True)
        db.add(wl)
        await db.flush()

    # Check for duplicate
    existing = await db.execute(
        select(WatchlistSymbol).where(
            WatchlistSymbol.watchlist_id == wl.id,
            WatchlistSymbol.symbol == data.symbol.upper(),
        )
    )
    if existing.scalar_one_or_none():
        return {"added": False, "reason": "Symbol already in watchlist"}

    ws = WatchlistSymbol(
        id=str(uuid.uuid4()),
        watchlist_id=wl.id,
        symbol=data.symbol.upper(),
        exchange=data.exchange.upper(),
        market_type=data.market_type,
    )
    db.add(ws)
    await db.commit()
    return {"added": True, "symbol": data.symbol.upper()}


@router.delete("/symbols/{symbol}", response_model=dict)
async def remove_symbol(symbol: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WatchlistSymbol).where(WatchlistSymbol.symbol == symbol.upper())
    )
    removed = 0
    for ws in result.scalars().all():
        await db.delete(ws)
        removed += 1
    await db.commit()
    return {"removed": removed, "symbol": symbol.upper()}


@router.post("/", response_model=dict, status_code=201)
async def create_watchlist(name: str, db: AsyncSession = Depends(get_db)):
    wl = Watchlist(id=str(uuid.uuid4()), name=name, is_default=False)
    db.add(wl)
    await db.commit()
    return {"id": wl.id, "name": wl.name}
