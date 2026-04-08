"""
Dashboard API — aggregated data for the home dashboard.
Returns all data needed to render the main screen in one request.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Any, Dict
import aiohttp

from app.core.database import get_db
from app.models.models import (
    Bot, Order, Position, Alert, BotStatus, BrokerConnector
)

router = APIRouter()


@router.get("/summary", response_model=Dict[str, Any])
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    """
    Return aggregated dashboard stats:
    - P&L summary
    - Active bots count
    - Open positions
    - Recent alerts
    - Portfolio value
    """
    # Active bots
    bot_result = await db.execute(
        select(func.count(Bot.id)).where(Bot.status == BotStatus.RUNNING)
    )
    active_bots = bot_result.scalar() or 0

    # Open positions count
    pos_result = await db.execute(
        select(func.count(Position.id)).where(Position.is_open == True)
    )
    open_positions = pos_result.scalar() or 0

    # Today's orders
    from datetime import datetime, date
    today_start = datetime.combine(date.today(), datetime.min.time())
    order_result = await db.execute(
        select(func.count(Order.id)).where(Order.placed_at >= today_start)
    )
    orders_today = order_result.scalar() or 0

    # Unread alerts
    alert_result = await db.execute(
        select(func.count(Alert.id)).where(Alert.is_read == False)
    )
    unread_alerts = alert_result.scalar() or 0

    # Recent positions for P&L (mock for now)
    pos_query = await db.execute(
        select(Position).where(Position.is_open == True).limit(10)
    )
    positions = pos_query.scalars().all()
    
    total_unrealized_pnl = sum(p.unrealized_pnl or 0.0 for p in positions)

    return {
        "active_bots": active_bots,
        "open_positions": open_positions,
        "orders_today": orders_today,
        "unread_alerts": unread_alerts,
        "unrealized_pnl": round(total_unrealized_pnl, 2),
        "realized_pnl_today": 0.0,  # TODO: compute from fills
        "total_pnl_today": round(total_unrealized_pnl, 2),
        "portfolio_value": 1_000_000.0,  # TODO: from portfolio service
        "trading_mode": "paper",  # TODO: from settings
    }


@router.get("/market-overview")
async def get_market_overview(
    market_scope: str = Query("all", pattern="^(all|indian|crypto|american)$"),
    db: AsyncSession = Depends(get_db),
):
    """
    Return market overview data (live or mock).
    In production, this pulls from the active market data connector.
    """
    result = await db.execute(select(BrokerConnector).where(BrokerConnector.enabled == True))
    enabled = {c.name.lower() for c in result.scalars().all()}

    has_crypto = "binance" in enabled or not enabled
    has_indian = any(x in enabled for x in {"groww", "angel_one", "upstox", "zerodha", "dhan"})
    has_american = any(x in enabled for x in {"alpaca", "ibkr"})

    wants = {
        "crypto": market_scope in {"all", "crypto"},
        "indian": market_scope in {"all", "indian"},
        "american": market_scope in {"all", "american"},
    }

    out = []
    if wants["crypto"] and has_crypto:
        out.extend(await _get_crypto_market_cards())

    # Keep indian/us empty unless corresponding brokers are enabled/implemented.
    if wants["indian"] and has_indian:
        out.extend([])
    if wants["american"] and has_american:
        out.extend([])

    return out


async def _get_crypto_market_cards() -> list[dict]:
    pairs = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as s:
        async with s.get("https://api.binance.com/api/v3/ticker/24hr") as r:
            if r.status >= 400:
                return []
            data = await r.json()
    by_symbol = {x.get("symbol"): x for x in data if x.get("symbol") in pairs}
    cards = []
    for p in pairs:
        d = by_symbol.get(p)
        if not d:
            continue
        cards.append(
            {
                "sym": p,
                "price": float(d.get("lastPrice", 0.0)),
                "chg": float(d.get("priceChange", 0.0)),
                "pct": float(d.get("priceChangePercent", 0.0)),
                "market": "crypto",
                "source": "binance",
            }
        )
    return cards
