"""
Dashboard API — real aggregated data from DB + live prices.
"""
from __future__ import annotations
from datetime import datetime, date
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import Bot, Order, Position, Alert, BotStatus, PortfolioSnapshot

router = APIRouter()


@router.get("/summary", response_model=Dict[str, Any])
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    """
    Real-time dashboard summary from DB + live Redis prices.
    """
    from app.services.market_stream import get_latest_price

    # Active bots
    active_bots = (await db.execute(
        select(func.count(Bot.id)).where(Bot.status == BotStatus.RUNNING)
    )).scalar() or 0

    # Open positions with live prices
    positions = (await db.execute(
        select(Position).where(Position.is_open)
    )).scalars().all()

    total_unrealized = 0.0
    positions_value  = 0.0
    for p in positions:
        tick = get_latest_price(p.symbol)
        cur  = float(tick["price"]) if tick else float(p.current_price or p.avg_price)
        p.current_price  = cur
        p.unrealized_pnl = (cur - float(p.avg_price)) * float(p.quantity)
        positions_value  += cur * float(p.quantity)
        total_unrealized += float(p.unrealized_pnl)

    # Commit mark-to-market updates
    if positions:
        await db.commit()

    # Today's orders
    today_start = datetime.combine(date.today(), datetime.min.time())
    orders_today = (await db.execute(
        select(func.count(Order.id)).where(Order.placed_at >= today_start)
    )).scalar() or 0

    # Unread alerts
    unread_alerts = (await db.execute(
        select(func.count(Alert.id)).where(Alert.is_read.is_(False))
    )).scalar() or 0

    # Cash from latest portfolio snapshot
    snap = (await db.execute(
        select(PortfolioSnapshot).order_by(PortfolioSnapshot.date.desc()).limit(1)
    )).scalars().first()
    cash = float(snap.cash) if snap else 1_000_000.0
    total_pnl = float(snap.total_pnl or 0) if snap else 0.0

    # Realized P&L today from fills
    from app.models.models import Fill
    (await db.execute(
        select(func.sum(Fill.price * Fill.quantity)).where(Fill.filled_at >= today_start)
    )).scalar() or 0.0

    total_value = cash + positions_value

    # Trading mode from settings
    from app.models.models import AppSetting
    mode_row = (await db.execute(
        select(AppSetting).where(AppSetting.key == "trading_mode")
    )).scalars().first()
    trading_mode = mode_row.value if mode_row else "paper"

    return {
        "active_bots":       active_bots,
        "open_positions":    len(positions),
        "orders_today":      orders_today,
        "unread_alerts":     unread_alerts,
        "unrealized_pnl":    round(total_unrealized, 2),
        "realized_pnl_today":round(total_pnl, 2),
        "total_pnl_today":   round(total_unrealized + total_pnl, 2),
        "portfolio_value":   round(total_value, 2),
        "cash":              round(cash, 2),
        "positions_value":   round(positions_value, 2),
        "trading_mode":      trading_mode,
        "timestamp":         datetime.utcnow().isoformat(),
    }


@router.get("/market-overview")
async def get_market_overview(
    market_scope: str = Query("all", pattern="^(all|indian|crypto|american)$"),
    db: AsyncSession = Depends(get_db),
):
    """Real market data from Redis (populated by market_stream)."""
    from app.services.market_stream import get_latest_price, DEFAULT_SYMBOLS, CRYPTO_SYMBOLS

    out = []
    scopes = set()
    if market_scope in ("all", "crypto"):
        scopes.add("crypto")
    if market_scope in ("all", "indian"):
        scopes.add("indian")

    for sym in DEFAULT_SYMBOLS:
        is_crypto = sym in CRYPTO_SYMBOLS
        if is_crypto and "crypto" not in scopes:
            continue
        if not is_crypto and "indian" not in scopes:
            continue

        tick = get_latest_price(sym)
        if tick:
            out.append({
                "sym":      sym,
                "price":    tick["price"],
                "exchange": tick.get("exchange", "MOCK"),
                "market":   "crypto" if is_crypto else "indian",
                "source":   "live",
            })

    # Add Binance 24h change if possible
    try:
        import aiohttp
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=4)) as s:
            async with s.get("https://api.binance.com/api/v3/ticker/24hr") as r:
                if r.status < 400:
                    ticker_data = await r.json()
                    by_sym = {d["symbol"]: d for d in ticker_data}
                    for item in out:
                        d = by_sym.get(item["sym"])
                        if d:
                            item["chg"]  = float(d.get("priceChange", 0))
                            item["pct"]  = float(d.get("priceChangePercent", 0))
    except Exception:
        pass

    return out
