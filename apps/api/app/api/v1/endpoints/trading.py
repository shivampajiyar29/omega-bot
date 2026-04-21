"""
Trading API — manual paper trade execution endpoint.
"""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class TradeRequest(BaseModel):
    symbol: str
    side: str           # buy | sell
    quantity: float
    price: Optional[float] = None  # if None, uses latest market price
    order_type: str = "market"


@router.post("/execute")
async def execute_trade(req: TradeRequest):
    """Execute a manual paper trade at live market price."""
    from app.services.market_stream import get_latest_price
    from app.services.paper_trading import place_paper_order

    # Use live price if not provided
    price = req.price
    if not price or price <= 0:
        tick = get_latest_price(req.symbol)
        if not tick:
            return {"error": f"No price data for {req.symbol}. Check market stream."}
        price = float(tick["price"])

    order = await place_paper_order(
        symbol=req.symbol.upper(),
        side=req.side.lower(),
        quantity=req.quantity,
        price=price,
    )
    if order:
        return {
            "success":      True,
            "order_id":     order.id,
            "symbol":       order.symbol,
            "side":         str(order.side.value),
            "quantity":     order.quantity,
            "fill_price":   order.avg_fill_price,
            "status":       str(order.status.value),
            "message":      f"✅ {req.side.upper()} {req.quantity} {req.symbol} @ {price:.4f}",
        }
    return {"success": False, "error": "Order rejected — check positions or price data"}


@router.get("/positions/summary")
async def positions_summary():
    """Live portfolio summary with mark-to-market P&L."""
    from app.core.database import AsyncSessionLocal
    from app.models.models import Position
    from app.services.market_stream import get_latest_price
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(Position).where(Position.is_open.is_(True))
        )).scalars().all()

        positions = []
        total_unrealized = 0.0
        total_invested   = 0.0

        for p in rows:
            tick = get_latest_price(p.symbol)
            cur  = float(tick["price"]) if tick else float(p.current_price or p.avg_price)
            unr  = (cur - float(p.avg_price)) * float(p.quantity)
            inv  = float(p.avg_price) * float(p.quantity)

            total_unrealized += unr
            total_invested   += inv

            positions.append({
                "symbol":        p.symbol,
                "side":          str(p.side.value),
                "quantity":      p.quantity,
                "avg_price":     p.avg_price,
                "current_price": round(cur, 4),
                "unrealized_pnl":round(unr, 2),
                "realized_pnl":  round(float(p.realized_pnl or 0), 2),
                "pnl_pct":       round(unr / inv * 100, 2) if inv > 0 else 0,
                "trading_mode":  str(p.trading_mode.value),
            })

        return {
            "positions":         positions,
            "total_unrealized":  round(total_unrealized, 2),
            "total_invested":    round(total_invested, 2),
            "open_count":        len(positions),
        }


@router.get("/signals")
async def get_current_signals():
    """Get current AI signals for all symbols from Redis."""
    from app.services.market_stream import DEFAULT_SYMBOLS, _get_redis, AI_SIGNAL_KEY_FMT
    import json
    try:
        r = _get_redis()
        signals = []
        for sym in DEFAULT_SYMBOLS:
            raw = r.get(AI_SIGNAL_KEY_FMT.format(symbol=sym))
            if raw:
                try:
                    signals.append(json.loads(raw))
                except Exception:
                    pass
        return signals
    except Exception:
        # Redis not available — return empty (signals appear once market stream starts)
        return []
