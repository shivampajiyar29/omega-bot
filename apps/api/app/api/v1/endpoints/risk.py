"""
Risk Management API — configure and monitor risk controls.
"""
from datetime import datetime, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
import uuid

from app.core.database import get_db
from app.models.models import RiskProfile, RiskEvent, Order, OrderStatus, Position

router = APIRouter()


class RiskProfileCreate(BaseModel):
    name: str
    max_daily_loss: float
    max_trade_loss: float
    max_open_positions: int
    max_order_value: float
    max_margin_pct: float = 80.0
    allowed_hours_start: Optional[str] = "09:15"
    allowed_hours_end: Optional[str] = "15:30"
    symbol_blacklist: List[str] = []
    symbol_whitelist: List[str] = []


@router.get("/profile", response_model=dict)
async def get_active_risk_profile(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RiskProfile).where(RiskProfile.is_active == True).limit(1)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        # Return defaults
        return {
            "name": "Default",
            "max_daily_loss": 5000.0,
            "max_trade_loss": 1000.0,
            "max_open_positions": 10,
            "max_order_value": 50000.0,
            "max_margin_pct": 80.0,
            "allowed_hours_start": "09:15",
            "allowed_hours_end": "15:30",
            "symbol_blacklist": [],
            "symbol_whitelist": [],
            "is_active": True,
        }
    return _rp(profile)


@router.get("/profiles", response_model=List[dict])
async def list_risk_profiles(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RiskProfile).order_by(RiskProfile.created_at.desc()))
    return [_rp(p) for p in result.scalars().all()]


@router.post("/profiles", response_model=dict, status_code=201)
async def create_risk_profile(data: RiskProfileCreate, db: AsyncSession = Depends(get_db)):
    profile = RiskProfile(
        id=str(uuid.uuid4()),
        **data.model_dump(),
        is_active=False,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return _rp(profile)


@router.post("/profiles/{profile_id}/activate")
async def activate_profile(profile_id: str, db: AsyncSession = Depends(get_db)):
    """Set a profile as the active risk profile."""
    # Deactivate all others
    result = await db.execute(select(RiskProfile))
    for p in result.scalars().all():
        p.is_active = p.id == profile_id
    await db.commit()
    return {"activated": True}


@router.get("/dashboard", response_model=dict)
async def get_risk_dashboard(db: AsyncSession = Depends(get_db)):
    """
    Live risk metrics for the risk dashboard card.
    """
    # Today's realized PnL from filled orders
    today = datetime.combine(date.today(), datetime.min.time())

    # Open positions count
    pos_result = await db.execute(
        select(func.count(Position.id)).where(Position.is_open == True)
    )
    open_pos = pos_result.scalar() or 0

    # Today's filled orders count
    order_result = await db.execute(
        select(func.count(Order.id)).where(
            Order.status == OrderStatus.FILLED,
            Order.placed_at >= today,
        )
    )
    orders_today = order_result.scalar() or 0

    # Get active profile limits
    profile = (await get_active_risk_profile(db))

    # Mock current values (in production, compute from real fills)
    current_daily_pnl = -1_230.0   # negative = loss today
    max_daily_loss = profile["max_daily_loss"]
    daily_loss_used_pct = min(abs(current_daily_pnl) / max_daily_loss * 100, 100)

    return {
        "daily_pnl": current_daily_pnl,
        "daily_loss_limit": max_daily_loss,
        "daily_loss_used_pct": round(daily_loss_used_pct, 1),
        "open_positions": open_pos,
        "max_positions": profile["max_open_positions"],
        "positions_used_pct": round(open_pos / profile["max_open_positions"] * 100, 1),
        "margin_used_pct": 42.0,    # TODO: from broker adapter
        "max_margin_pct": profile["max_margin_pct"],
        "orders_today": orders_today,
        "kill_switch_active": False,
        "within_trading_hours": True,
        "profile_name": profile["name"],
    }


@router.get("/events", response_model=List[dict])
async def get_risk_events(limit: int = 20, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RiskEvent).order_by(RiskEvent.occurred_at.desc()).limit(limit)
    )
    return [
        {
            "id": e.id,
            "type": e.event_type,
            "severity": e.severity,
            "message": e.message,
            "occurred_at": e.occurred_at.isoformat(),
        }
        for e in result.scalars().all()
    ]


def _rp(p: RiskProfile) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "max_daily_loss": p.max_daily_loss,
        "max_trade_loss": p.max_trade_loss,
        "max_open_positions": p.max_open_positions,
        "max_order_value": p.max_order_value,
        "max_margin_pct": p.max_margin_pct,
        "allowed_hours_start": p.allowed_hours_start,
        "allowed_hours_end": p.allowed_hours_end,
        "symbol_blacklist": p.symbol_blacklist or [],
        "symbol_whitelist": p.symbol_whitelist or [],
        "is_active": p.is_active,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }
