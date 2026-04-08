"""
Module Manager API — enable/disable feature modules.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.models.models import EnabledModule

router = APIRouter()

# Default module catalogue (shown even before DB records exist)
DEFAULT_MODULES = [
    {"name": "dashboard",           "enabled": True,  "description": "Main dashboard overview"},
    {"name": "watchlist",           "enabled": True,  "description": "Symbol watchlist with live prices"},
    {"name": "charts",              "enabled": True,  "description": "Candlestick charts with indicators"},
    {"name": "strategy_builder",    "enabled": True,  "description": "Visual and DSL strategy creation"},
    {"name": "backtester",          "enabled": True,  "description": "Historical strategy backtesting"},
    {"name": "paper_trading",       "enabled": True,  "description": "Simulated trading with mock broker"},
    {"name": "live_trading",        "enabled": False, "description": "Real-money trading"},
    {"name": "orders",              "enabled": True,  "description": "Order management and history"},
    {"name": "positions",           "enabled": True,  "description": "Open and closed position tracker"},
    {"name": "portfolio",           "enabled": True,  "description": "Portfolio analytics and equity curve"},
    {"name": "risk_management",     "enabled": True,  "description": "Risk controls and guardrails"},
    {"name": "logs",                "enabled": True,  "description": "System and trade audit logs"},
    {"name": "alerts",              "enabled": True,  "description": "Price and event notifications"},
    {"name": "connectors",          "enabled": True,  "description": "Broker and data API connections"},
    {"name": "ai_assistant",        "enabled": False, "description": "AI strategy generation assistant"},
    {"name": "options_analytics",   "enabled": False, "description": "Options Greeks and IV viewer"},
    {"name": "screener",            "enabled": False, "description": "Multi-symbol strategy screener"},
    {"name": "scanner",             "enabled": False, "description": "Real-time signal scanner"},
    {"name": "trade_journal",       "enabled": False, "description": "Manual trade notes and analytics"},
    {"name": "webhook_automation",  "enabled": False, "description": "TradingView and external webhooks"},
]


class ModuleUpdate(BaseModel):
    enabled: bool
    config: Optional[dict] = None


@router.get("/", response_model=List[dict])
async def list_modules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EnabledModule))
    db_modules = {m.name: m for m in result.scalars().all()}

    out = []
    for m in DEFAULT_MODULES:
        if m["name"] in db_modules:
            dm = db_modules[m["name"]]
            out.append({
                "name":        dm.name,
                "enabled":     dm.enabled,
                "config":      dm.config,
                "description": m["description"],
                "updated_at":  dm.updated_at.isoformat() if dm.updated_at else None,
            })
        else:
            out.append({**m, "config": None, "updated_at": None})
    return out


@router.get("/{name}", response_model=dict)
async def get_module(name: str, db: AsyncSession = Depends(get_db)):
    mod = await db.get(EnabledModule, name)
    default = next((m for m in DEFAULT_MODULES if m["name"] == name), None)
    if not mod and not default:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Module '{name}' not found")
    if mod:
        return {"name": mod.name, "enabled": mod.enabled, "config": mod.config}
    return default


@router.patch("/{name}", response_model=dict)
async def update_module(name: str, data: ModuleUpdate, db: AsyncSession = Depends(get_db)):
    mod = await db.get(EnabledModule, name)
    if mod:
        mod.enabled = data.enabled
        if data.config is not None:
            mod.config = data.config
    else:
        mod = EnabledModule(
            name=name,
            enabled=data.enabled,
            config=data.config,
            description=next((m["description"] for m in DEFAULT_MODULES if m["name"] == name), ""),
        )
        db.add(mod)
    await db.commit()
    return {"name": name, "enabled": data.enabled, "updated": True}


@router.post("/{name}/enable", response_model=dict)
async def enable_module(name: str, db: AsyncSession = Depends(get_db)):
    return await update_module(name, ModuleUpdate(enabled=True), db)


@router.post("/{name}/disable", response_model=dict)
async def disable_module(name: str, db: AsyncSession = Depends(get_db)):
    return await update_module(name, ModuleUpdate(enabled=False), db)
