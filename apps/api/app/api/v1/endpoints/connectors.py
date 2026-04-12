"""
Connectors API — broker and market data connector management.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import uuid

from app.core.database import get_db
from app.models.models import BrokerConnector, MarketDataConnector, ConnectorStatus
from app.connectors.registry import list_brokers, list_marketdata_adapters, get_broker_adapter

router = APIRouter()


# ─── Broker Connectors ────────────────────────────────────────────────────────

class ConnectorCreate(BaseModel):
    name: str
    display_name: str
    adapter_class: str
    trading_mode: str = "paper"
    market_types: List[str] = []
    config: Optional[dict] = None


@router.get("/brokers", response_model=List[dict])
async def list_broker_connectors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BrokerConnector).order_by(BrokerConnector.name))
    db_connectors = {c.name: c for c in result.scalars().all()}

    # Merge registry info with DB records
    registered = list_brokers()
    out = []
    for r in registered:
        db_c = db_connectors.get(r["name"])
        if db_c:
            out.append(_bc(db_c))
        else:
            out.append({
                **r,
                "status": "disconnected" if r["name"] != "mock" else "connected",
                "enabled": r["name"] == "mock",
                "is_default": r["name"] == "mock",
                "trading_mode": "paper",
                "config": None,
            })
    return out


@router.get("/brokers/{name}", response_model=dict)
async def get_broker(name: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BrokerConnector).where(BrokerConnector.name == name))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail=f"Broker connector '{name}' not found")
    return _bc(c)


@router.post("/brokers/{name}/enable", response_model=dict)
async def enable_broker(name: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BrokerConnector).where(BrokerConnector.name == name))
    c = result.scalar_one_or_none()
    if c:
        c.enabled = True
    else:
        c = BrokerConnector(id=str(uuid.uuid4()), name=name, display_name=name.title(),
                            adapter_class=f"app.adapters.broker.{name}.{name.title()}BrokerAdapter",
                            enabled=True, status=ConnectorStatus.DISCONNECTED)
        db.add(c)
    await db.commit()
    return {"name": name, "enabled": True}


@router.post("/brokers/{name}/disable", response_model=dict)
async def disable_broker(name: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BrokerConnector).where(BrokerConnector.name == name))
    c = result.scalar_one_or_none()
    if c:
        c.enabled = False
        if c.is_default:
            c.is_default = False
        await db.commit()
    return {"name": name, "enabled": False}


@router.post("/brokers/{name}/set-default", response_model=dict)
async def set_default_broker(name: str, db: AsyncSession = Depends(get_db)):
    """Set a connector as the active default broker."""
    # Clear existing default
    result = await db.execute(select(BrokerConnector).where(BrokerConnector.is_default))
    for c in result.scalars().all():
        c.is_default = False

    # Set new default
    result2 = await db.execute(select(BrokerConnector).where(BrokerConnector.name == name))
    c = result2.scalar_one_or_none()
    if c:
        c.is_default = True
        c.enabled = True
    await db.commit()
    return {"name": name, "is_default": True}


@router.post("/brokers/{name}/test", response_model=dict)
async def test_broker_connection(name: str):
    """Test connectivity to a broker."""
    try:
        adapter = get_broker_adapter(name)
        connected = await adapter.connect()
        await adapter.disconnect()
        return {"name": name, "status": "ok" if connected else "failed",
                "message": "Connected successfully" if connected else "Connection failed"}
    except Exception as e:
        return {"name": name, "status": "error", "message": str(e)}


@router.patch("/brokers/{name}/config", response_model=dict)
async def update_broker_config(name: str, config: dict, db: AsyncSession = Depends(get_db)):
    """Update broker API credentials/config."""
    result = await db.execute(select(BrokerConnector).where(BrokerConnector.name == name))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Connector not found")
    # NOTE: In production, encrypt sensitive fields before storing
    c.config = config
    c.status = ConnectorStatus.DISCONNECTED  # Needs re-test after config change
    await db.commit()
    return {"name": name, "config_updated": True}


# ─── Market Data Connectors ───────────────────────────────────────────────────

@router.get("/marketdata", response_model=List[dict])
async def list_md_connectors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MarketDataConnector).order_by(MarketDataConnector.name))
    db_connectors = {c.name: c for c in result.scalars().all()}

    registered = list_marketdata_adapters()
    out = []
    for r in registered:
        db_c = db_connectors.get(r["name"])
        if db_c:
            out.append(_mdc(db_c))
        else:
            out.append({
                **r,
                "status": "connected" if r["name"] == "mock" else "disconnected",
                "enabled": r["name"] == "mock",
                "supported_markets": ["all"],
                "config": None,
            })
    return out


@router.get("/marketdata/{name}", response_model=dict)
async def get_md_connector(name: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MarketDataConnector).where(MarketDataConnector.name == name))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail=f"Market data connector '{name}' not found")
    return _mdc(c)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _bc(c: BrokerConnector) -> dict:
    return {
        "id":           c.id,
        "name":         c.name,
        "display_name": c.display_name,
        "adapter_class":c.adapter_class,
        "status":       c.status,
        "enabled":      c.enabled,
        "is_default":   c.is_default,
        "trading_mode": c.trading_mode,
        "market_types": c.market_types or [],
        "created_at":   c.created_at.isoformat() if c.created_at else None,
        "updated_at":   c.updated_at.isoformat() if c.updated_at else None,
    }


def _mdc(c: MarketDataConnector) -> dict:
    return {
        "id":               c.id,
        "name":             c.name,
        "display_name":     c.display_name,
        "adapter_class":    c.adapter_class,
        "status":           c.status,
        "enabled":          c.enabled,
        "supported_markets":c.supported_markets or [],
        "created_at":       c.created_at.isoformat() if c.created_at else None,
    }
