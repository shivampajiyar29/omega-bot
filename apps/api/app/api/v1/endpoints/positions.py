"""
Positions API — open and closed position tracking.
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.models.models import Position, OrderSide

router = APIRouter()


@router.get("", response_model=List[dict], include_in_schema=False)
@router.get("/", response_model=List[dict])
async def list_positions(
    open_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    q = select(Position).order_by(Position.opened_at.desc())
    if open_only:
        q = q.where(Position.is_open == True)
    result = await db.execute(q)
    return [_p(p) for p in result.scalars().all()]


@router.get("/{position_id}", response_model=dict)
async def get_position(position_id: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(Position, position_id)
    if not p:
        raise HTTPException(status_code=404, detail="Position not found")
    return _p(p)


@router.post("/{position_id}/close", response_model=dict)
async def close_position(position_id: str, db: AsyncSession = Depends(get_db)):
    """
    Mark a position as closed (for paper trading reconciliation).
    In live mode, closing happens via order fills automatically.
    """
    p = await db.get(Position, position_id)
    if not p:
        raise HTTPException(status_code=404, detail="Position not found")
    if not p.is_open:
        raise HTTPException(status_code=400, detail="Position already closed")

    p.is_open = False
    p.closed_at = datetime.utcnow()
    await db.commit()
    return {"closed": True, "position_id": position_id}


@router.get("/summary/pnl", response_model=dict)
async def get_pnl_summary(db: AsyncSession = Depends(get_db)):
    """Aggregate P&L across all open positions."""
    result = await db.execute(select(Position).where(Position.is_open == True))
    positions = result.scalars().all()

    unrealized = sum(p.unrealized_pnl or 0.0 for p in positions)
    realized = sum(p.realized_pnl for p in positions)

    return {
        "open_count":      len(positions),
        "unrealized_pnl":  round(unrealized, 2),
        "realized_pnl":    round(realized, 2),
        "total_pnl":       round(unrealized + realized, 2),
    }


def _p(p: Position) -> dict:
    return {
        "id":            p.id,
        "symbol":        p.symbol,
        "exchange":      p.exchange,
        "market_type":   p.market_type,
        "side":          p.side,
        "quantity":      p.quantity,
        "avg_price":     p.avg_price,
        "current_price": p.current_price,
        "unrealized_pnl":p.unrealized_pnl,
        "realized_pnl":  p.realized_pnl,
        "is_open":       p.is_open,
        "trading_mode":  p.trading_mode,
        "connector_id":  p.connector_id,
        "opened_at":     p.opened_at.isoformat() if p.opened_at else None,
        "closed_at":     p.closed_at.isoformat() if p.closed_at else None,
        "updated_at":    p.updated_at.isoformat() if p.updated_at else None,
    }
