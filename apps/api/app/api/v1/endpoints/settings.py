"""
Settings API — global application settings key/value store.
"""
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.models.models import AppSetting

router = APIRouter()

# Default settings returned when DB has no entries yet
DEFAULTS: Dict[str, Any] = {
    "trading_mode":            "paper",
    "initial_capital":         1_000_000,
    "currency":                "INR",
    "timezone":                "Asia/Kolkata",
    "default_max_daily_loss":  5000,
    "default_max_trade_loss":  1000,
    "default_max_positions":   10,
    "default_max_order_value": 50000,
    "notifications_enabled":   False,
    "theme":                   "dark",
}


class SettingUpdate(BaseModel):
    value: Any
    description: str = ""


@router.get("/", response_model=Dict[str, Any])
async def get_all_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AppSetting))
    db_settings = {s.key: s.value for s in result.scalars().all()}
    # Merge defaults with DB overrides
    return {**DEFAULTS, **db_settings}


@router.get("/{key}")
async def get_setting(key: str, db: AsyncSession = Depends(get_db)):
    s = await db.get(AppSetting, key)
    if s:
        return {"key": key, "value": s.value}
    if key in DEFAULTS:
        return {"key": key, "value": DEFAULTS[key], "is_default": True}
    raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")


@router.patch("/{key}", response_model=dict)
async def update_setting(key: str, data: SettingUpdate, db: AsyncSession = Depends(get_db)):
    s = await db.get(AppSetting, key)
    if s:
        s.value = data.value
        if data.description:
            s.description = data.description
    else:
        s = AppSetting(key=key, value=data.value, description=data.description)
        db.add(s)
    await db.commit()
    return {"key": key, "value": data.value, "updated": True}


@router.post("/bulk", response_model=dict)
async def update_bulk(settings: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """Update multiple settings in one call."""
    for key, value in settings.items():
        s = await db.get(AppSetting, key)
        if s:
            s.value = value
        else:
            db.add(AppSetting(key=key, value=value))
    await db.commit()
    return {"updated": list(settings.keys())}


@router.delete("/{key}", response_model=dict)
async def reset_setting(key: str, db: AsyncSession = Depends(get_db)):
    """Reset a setting to its default value."""
    s = await db.get(AppSetting, key)
    if s:
        await db.delete(s)
        await db.commit()
    return {"key": key, "reset": True, "default": DEFAULTS.get(key)}
