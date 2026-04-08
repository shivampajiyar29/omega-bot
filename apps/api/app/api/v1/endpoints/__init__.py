"""
Stub endpoints for modules not yet fully implemented.
Each returns appropriate mock/empty data so the frontend works.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
import uuid
from datetime import datetime

from app.core.database import get_db
from app.models.models import Order, Position, Alert, AuditLog, EnabledModule, AppSetting, BrokerConnector, MarketDataConnector, Watchlist, WatchlistSymbol


# ── Orders ────────────────────────────────────────────────────────────────────
orders = APIRouter()

@orders.get("/")
async def list_orders(status: Optional[str] = None, symbol: Optional[str] = None, limit: int = 50, db: AsyncSession = Depends(get_db)):
    q = select(Order).order_by(Order.placed_at.desc()).limit(limit)
    result = await db.execute(q)
    return [_order(o) for o in result.scalars().all()]

@orders.post("/{order_id}/cancel")
async def cancel_order(order_id: str, db: AsyncSession = Depends(get_db)):
    from app.models.models import OrderStatus
    o = await db.get(Order, order_id)
    if not o:
        from fastapi import HTTPException
        raise HTTPException(404, "Order not found")
    o.status = OrderStatus.CANCELLED
    await db.commit()
    return {"cancelled": True}

def _order(o: Order) -> dict:
    return {"id": o.id, "symbol": o.symbol, "exchange": o.exchange, "side": o.side, "order_type": o.order_type, "quantity": o.quantity, "price": o.price, "status": o.status, "filled_quantity": o.filled_quantity, "avg_fill_price": o.avg_fill_price, "trading_mode": o.trading_mode, "placed_at": o.placed_at.isoformat() if o.placed_at else None}


# ── Positions ─────────────────────────────────────────────────────────────────
positions = APIRouter()

@positions.get("/")
async def list_positions(open_only: bool = True, db: AsyncSession = Depends(get_db)):
    q = select(Position)
    if open_only:
        q = q.where(Position.is_open == True)
    result = await db.execute(q.order_by(Position.opened_at.desc()))
    return [_pos(p) for p in result.scalars().all()]

def _pos(p: Position) -> dict:
    return {"id": p.id, "symbol": p.symbol, "exchange": p.exchange, "side": p.side, "quantity": p.quantity, "avg_price": p.avg_price, "current_price": p.current_price, "unrealized_pnl": p.unrealized_pnl, "realized_pnl": p.realized_pnl, "is_open": p.is_open, "trading_mode": p.trading_mode, "opened_at": p.opened_at.isoformat() if p.opened_at else None}


# ── Alerts ────────────────────────────────────────────────────────────────────
alerts = APIRouter()

@alerts.get("/")
async def list_alerts(unread_only: bool = False, limit: int = 50, db: AsyncSession = Depends(get_db)):
    q = select(Alert).order_by(Alert.created_at.desc()).limit(limit)
    if unread_only:
        q = q.where(Alert.is_read == False)
    result = await db.execute(q)
    return [{"id": a.id, "title": a.title, "message": a.message, "level": a.level, "is_read": a.is_read, "created_at": a.created_at.isoformat()} for a in result.scalars().all()]

@alerts.post("/{alert_id}/read")
async def mark_read(alert_id: str, db: AsyncSession = Depends(get_db)):
    a = await db.get(Alert, alert_id)
    if a:
        a.is_read = True
        await db.commit()
    return {"ok": True}

@alerts.post("/read-all")
async def mark_all_read(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alert).where(Alert.is_read == False))
    for a in result.scalars().all():
        a.is_read = True
    await db.commit()
    return {"ok": True}


# ── Logs ──────────────────────────────────────────────────────────────────────
logs = APIRouter()

@logs.get("/")
async def list_logs(limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditLog).order_by(AuditLog.logged_at.desc()).limit(limit))
    return [{"id": l.id, "action": l.action, "entity_type": l.entity_type, "entity_id": l.entity_id, "details": l.details, "logged_at": l.logged_at.isoformat()} for l in result.scalars().all()]


# ── Modules ───────────────────────────────────────────────────────────────────
modules = APIRouter()

class ModuleUpdate(BaseModel):
    enabled: bool
    config: Optional[dict] = None

DEFAULT_MODULES = [
    {"name": "dashboard", "enabled": True, "description": "Main dashboard"},
    {"name": "watchlist", "enabled": True, "description": "Symbol watchlist"},
    {"name": "charts", "enabled": True, "description": "Candlestick charts"},
    {"name": "strategy_builder", "enabled": True, "description": "Strategy builder"},
    {"name": "backtester", "enabled": True, "description": "Backtesting engine"},
    {"name": "paper_trading", "enabled": True, "description": "Paper trading"},
    {"name": "live_trading", "enabled": False, "description": "Live trading"},
    {"name": "orders", "enabled": True, "description": "Order management"},
    {"name": "positions", "enabled": True, "description": "Position tracker"},
    {"name": "portfolio", "enabled": True, "description": "Portfolio analytics"},
    {"name": "risk_management", "enabled": True, "description": "Risk controls"},
    {"name": "logs", "enabled": True, "description": "Audit logs"},
    {"name": "alerts", "enabled": True, "description": "Alert system"},
    {"name": "connectors", "enabled": True, "description": "Broker connectors"},
    {"name": "ai_assistant", "enabled": False, "description": "AI strategy assistant"},
    {"name": "options_analytics", "enabled": False, "description": "Options analytics"},
    {"name": "screener", "enabled": False, "description": "Stock screener"},
    {"name": "trade_journal", "enabled": False, "description": "Trade journal"},
    {"name": "webhook_automation", "enabled": False, "description": "Webhook signals"},
]

@modules.get("/")
async def list_modules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EnabledModule))
    db_modules = {m.name: m for m in result.scalars().all()}
    out = []
    for m in DEFAULT_MODULES:
        if m["name"] in db_modules:
            dm = db_modules[m["name"]]
            out.append({"name": dm.name, "enabled": dm.enabled, "config": dm.config, "description": m["description"]})
        else:
            out.append(m)
    return out

@modules.patch("/{module_name}")
async def update_module(module_name: str, data: ModuleUpdate, db: AsyncSession = Depends(get_db)):
    mod = await db.get(EnabledModule, module_name)
    if mod:
        mod.enabled = data.enabled
        if data.config:
            mod.config = data.config
    else:
        db.add(EnabledModule(name=module_name, enabled=data.enabled, config=data.config))
    await db.commit()
    return {"name": module_name, "enabled": data.enabled}


# ── Settings ──────────────────────────────────────────────────────────────────
settings_router = APIRouter()

@settings_router.get("/")
async def get_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AppSetting))
    return {s.key: s.value for s in result.scalars().all()}

class SettingUpdate(BaseModel):
    value: object

@settings_router.patch("/{key}")
async def update_setting(key: str, data: SettingUpdate, db: AsyncSession = Depends(get_db)):
    s = await db.get(AppSetting, key)
    if s:
        s.value = data.value
    else:
        db.add(AppSetting(key=key, value=data.value))
    await db.commit()
    return {"key": key, "value": data.value}


# ── Watchlist ─────────────────────────────────────────────────────────────────
watchlist_router = APIRouter()

@watchlist_router.get("/")
async def get_watchlist(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Watchlist).where(Watchlist.is_default == True).limit(1))
    wl = result.scalar_one_or_none()
    if not wl:
        # Return mock data
        return {"id": "default", "name": "My Watchlist", "symbols": [
            {"symbol": "RELIANCE", "exchange": "NSE", "market_type": "equity"},
            {"symbol": "TCS", "exchange": "NSE", "market_type": "equity"},
            {"symbol": "INFY", "exchange": "NSE", "market_type": "equity"},
            {"symbol": "BTCUSDT", "exchange": "BINANCE", "market_type": "crypto"},
        ]}
    syms = await db.execute(select(WatchlistSymbol).where(WatchlistSymbol.watchlist_id == wl.id))
    return {"id": wl.id, "name": wl.name, "symbols": [{"symbol": s.symbol, "exchange": s.exchange, "market_type": s.market_type} for s in syms.scalars().all()]}

class AddSymbol(BaseModel):
    symbol: str
    exchange: str
    market_type: str = "equity"

@watchlist_router.post("/symbols")
async def add_symbol(data: AddSymbol, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Watchlist).where(Watchlist.is_default == True).limit(1))
    wl = result.scalar_one_or_none()
    if not wl:
        wl = Watchlist(id=str(uuid.uuid4()), name="My Watchlist", is_default=True)
        db.add(wl)
        await db.flush()
    db.add(WatchlistSymbol(id=str(uuid.uuid4()), watchlist_id=wl.id, symbol=data.symbol, exchange=data.exchange, market_type=data.market_type))
    await db.commit()
    return {"added": True}

@watchlist_router.delete("/symbols/{symbol}")
async def remove_symbol(symbol: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WatchlistSymbol).where(WatchlistSymbol.symbol == symbol))
    for ws in result.scalars().all():
        await db.delete(ws)
    await db.commit()
    return {"removed": True}


# ── Connectors ────────────────────────────────────────────────────────────────
connectors_router = APIRouter()

@connectors_router.get("/brokers")
async def list_broker_connectors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BrokerConnector))
    connectors = result.scalars().all()
    if not connectors:
        return _default_broker_connectors()
    return [_bc(c) for c in connectors]

@connectors_router.get("/marketdata")
async def list_md_connectors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MarketDataConnector))
    connectors = result.scalars().all()
    if not connectors:
        return _default_md_connectors()
    return [_mdc(c) for c in connectors]

@connectors_router.post("/brokers/{name}/test")
async def test_broker_connection(name: str):
    return {"status": "ok" if name == "mock" else "not_configured", "message": f"{'Mock broker is always connected' if name == 'mock' else 'Add API keys in Settings to connect'}"}

def _default_broker_connectors():
    return [
        {"name": "mock", "display_name": "Mock Broker", "status": "connected", "enabled": True, "is_default": True, "trading_mode": "paper", "market_types": ["equity","futures","crypto","forex"]},
        {"name": "zerodha", "display_name": "Zerodha / Kite", "status": "disconnected", "enabled": False, "is_default": False, "market_types": ["equity","futures","options"]},
        {"name": "angel_one", "display_name": "Angel One", "status": "disconnected", "enabled": False, "is_default": False, "market_types": ["equity","futures","options"]},
        {"name": "dhan", "display_name": "Dhan", "status": "disconnected", "enabled": False, "is_default": False, "market_types": ["equity","futures","options"]},
        {"name": "upstox", "display_name": "Upstox", "status": "disconnected", "enabled": False, "is_default": False, "market_types": ["equity","futures"]},
        {"name": "alpaca", "display_name": "Alpaca (US)", "status": "disconnected", "enabled": False, "is_default": False, "market_types": ["equity"]},
        {"name": "binance", "display_name": "Binance", "status": "disconnected", "enabled": False, "is_default": False, "market_types": ["crypto"]},
    ]

def _default_md_connectors():
    return [
        {"name": "mock", "display_name": "Mock Data", "status": "connected", "enabled": True, "supported_markets": ["equity","futures","crypto","forex"]},
        {"name": "csv", "display_name": "CSV Files", "status": "disconnected", "enabled": False, "supported_markets": ["all"]},
    ]

def _bc(c: BrokerConnector) -> dict:
    return {"id": c.id, "name": c.name, "display_name": c.display_name, "status": c.status, "enabled": c.enabled, "is_default": c.is_default, "trading_mode": c.trading_mode, "market_types": c.market_types or []}

def _mdc(c: MarketDataConnector) -> dict:
    return {"id": c.id, "name": c.name, "display_name": c.display_name, "status": c.status, "enabled": c.enabled, "supported_markets": c.supported_markets or []}


# ── Portfolio ─────────────────────────────────────────────────────────────────
portfolio_router = APIRouter()

@portfolio_router.get("/summary")
async def get_portfolio_summary():
    return {
        "total_value": 324_580.0,
        "cash": 198_320.0,
        "positions_value": 126_260.0,
        "total_pnl": 24_580.0,
        "total_return_pct": 8.22,
        "day_pnl": 1_840.0,
        "day_return_pct": 0.57,
        "allocation": [
            {"name": "Cash", "value": 198_320, "pct": 61.1},
            {"name": "Equities", "value": 96_260, "pct": 29.7},
            {"name": "Futures", "value": 30_000, "pct": 9.2},
        ]
    }

@portfolio_router.get("/equity-curve")
async def get_equity_curve(period: str = "1m"):
    import random, math
    points = 30 if period == "1m" else (7 if period == "1w" else 365)
    val = 300_000.0
    curve = []
    for i in range(points):
        val *= (1 + random.gauss(0.001, 0.008))
        curve.append({"date": f"2024-{(i//30)+1:02d}-{(i%30)+1:02d}", "value": round(val, 2)})
    return curve


# ── Market Data ───────────────────────────────────────────────────────────────
marketdata_router = APIRouter()

@marketdata_router.get("/search")
async def search_instruments(q: str = ""):
    from app.adapters.marketdata.mock_data import MockMarketDataAdapter
    adapter = MockMarketDataAdapter()
    return await adapter.search_instruments(q)

@marketdata_router.get("/ohlcv")
async def get_ohlcv(symbol: str, exchange: str, timeframe: str = "15m", from_: Optional[str] = None, to: Optional[str] = None):
    from app.adapters.marketdata.mock_data import MockMarketDataAdapter
    from datetime import timedelta
    adapter = MockMarketDataAdapter()
    await adapter.connect()
    end = datetime.utcnow()
    start = end - timedelta(days=30)
    if from_:
        start = datetime.fromisoformat(from_)
    if to:
        end = datetime.fromisoformat(to)
    bars = await adapter.get_historical_ohlcv(symbol, exchange, timeframe, start, end)
    return [{"t": b.timestamp.isoformat(), "o": b.open, "h": b.high, "l": b.low, "c": b.close, "v": b.volume} for b in bars]


# ── Webhooks ──────────────────────────────────────────────────────────────────
webhooks_router = APIRouter()

class WebhookSignal(BaseModel):
    symbol: str
    action: str  # buy | sell | exit
    price: Optional[float] = None
    quantity: Optional[float] = None
    strategy: Optional[str] = None
    secret: Optional[str] = None

@webhooks_router.post("/tradingview")
async def tradingview_webhook(signal: WebhookSignal):
    from app.core.config import settings
    if settings.TRADINGVIEW_WEBHOOK_SECRET and signal.secret != settings.TRADINGVIEW_WEBHOOK_SECRET:
        from fastapi import HTTPException
        raise HTTPException(403, "Invalid webhook secret")
    # TODO: route to execution engine
    return {"received": True, "symbol": signal.symbol, "action": signal.action}
