"""
Orders API — order management and history.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.models.models import Order, OrderStatus

router = APIRouter()


@router.get("", response_model=List[dict], include_in_schema=False)
@router.get("/", response_model=List[dict])
async def list_orders(
    status: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    q = select(Order).order_by(Order.placed_at.desc()).limit(limit)
    if status:
        try:
            q = q.where(Order.status == OrderStatus(status))
        except ValueError:
            pass
    if symbol:
        q = q.where(Order.symbol == symbol.upper())

    result = await db.execute(q)
    return [_o(o) for o in result.scalars().all()]


@router.get("/{order_id}", response_model=dict)
async def get_order(order_id: str, db: AsyncSession = Depends(get_db)):
    o = await db.get(Order, order_id)
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    return _o(o)


@router.post("/{order_id}/cancel", response_model=dict)
async def cancel_order(order_id: str, db: AsyncSession = Depends(get_db)):
    o = await db.get(Order, order_id)
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    if o.status not in (OrderStatus.OPEN, OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED):
        raise HTTPException(status_code=400, detail=f"Cannot cancel order in status: {o.status}")
    o.status = OrderStatus.CANCELLED
    await db.commit()
    return {"cancelled": True, "order_id": order_id}


@router.post("/cancel-all", response_model=dict)
async def cancel_all_open(symbol: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    q = select(Order).where(Order.status.in_([OrderStatus.OPEN, OrderStatus.PENDING]))
    if symbol:
        q = q.where(Order.symbol == symbol.upper())
    result = await db.execute(q)
    orders = result.scalars().all()
    for o in orders:
        o.status = OrderStatus.CANCELLED
    await db.commit()
    return {"cancelled": len(orders)}


def _o(o: Order) -> dict:
    return {
        "id": o.id,
        "symbol": o.symbol,
        "exchange": o.exchange,
        "market_type": o.market_type,
        "side": o.side,
        "order_type": o.order_type,
        "quantity": o.quantity,
        "price": o.price,
        "stop_price": o.stop_price,
        "status": o.status,
        "filled_quantity": o.filled_quantity,
        "avg_fill_price": o.avg_fill_price,
        "trading_mode": o.trading_mode,
        "bot_id": o.bot_id,
        "tags": o.tags or {},
        "placed_at": o.placed_at.isoformat() if o.placed_at else None,
        "updated_at": o.updated_at.isoformat() if o.updated_at else None,
    }
