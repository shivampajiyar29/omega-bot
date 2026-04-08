"""
Lightweight WebSocket endpoints used by the local dashboard.
"""
import asyncio
import json
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services import market_stream
from app.core.database import AsyncSessionLocal
from sqlalchemy import select, desc, func
from app.models.models import Order, Position, Alert, PortfolioSnapshot

router = APIRouter()

_BASE_PRICES = {
    "RELIANCE": 2847.30,
    "TCS": 3912.60,
    "INFY": 1834.90,
    "HDFC": 1672.15,
    "NIFTY50": 24832.15,
    "BTCUSDT": 87432.00,
}


@router.websocket("/ws/market")
async def market_feed(websocket: WebSocket) -> None:
    await websocket.accept()
    symbols = ["RELIANCE", "TCS", "INFY"]

    try:
        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=1.5)
                payload = json.loads(raw)
                if payload.get("action") == "subscribe" and payload.get("symbols"):
                    symbols = [str(symbol).upper() for symbol in payload["symbols"]]
                elif payload.get("action") == "unsubscribe" and payload.get("symbols"):
                    remove = {str(symbol).upper() for symbol in payload["symbols"]}
                    symbols = [symbol for symbol in symbols if symbol not in remove]
            except TimeoutError:
                pass

            for symbol in symbols:
                tick = market_stream.get_latest_price(symbol)
                if tick:
                    price = float(tick["price"])
                    ex = tick.get("exchange", "MOCK")
                    ts = tick.get("timestamp", datetime.now(timezone.utc).isoformat())
                else:
                    base = _BASE_PRICES.get(symbol, 1000.0)
                    price = round(base * (1 + random.uniform(-0.002, 0.002)), 2)
                    _BASE_PRICES[symbol] = price
                    ex = "MOCK"
                    ts = datetime.now(timezone.utc).isoformat()

                await websocket.send_json(
                    {
                        "type": "tick",
                        "symbol": symbol,
                        "exchange": ex,
                        "price": price,
                        "timestamp": ts,
                    }
                )
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return


@router.websocket("/ws/bots")
async def bot_feed(websocket: WebSocket) -> None:
    await websocket.accept()

    try:
        while True:
            await websocket.send_json(
                {
                    "type": "bot_update",
                    "bots": [
                        {"id": "ema-bot", "name": "EMA Bot", "status": "running", "pnl": round(random.uniform(-1200, 3500), 2)},
                        {"id": "rsi-bot", "name": "RSI Bot", "status": "paper", "pnl": round(random.uniform(-700, 2100), 2)},
                    ],
                }
            )
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _fetch_orders(limit: int = 50) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(select(Order).order_by(desc(Order.placed_at)).limit(limit))
        ).scalars().all()
        items: List[Dict[str, Any]] = []
        last_ts: Optional[str] = None
        for o in rows:
            ts = (o.updated_at or o.placed_at)
            iso = ts.replace(tzinfo=timezone.utc).isoformat() if ts else None
            if iso and (last_ts is None or iso > last_ts):
                last_ts = iso
            items.append(
                {
                    "id": o.id,
                    "symbol": o.symbol,
                    "exchange": o.exchange,
                    "side": getattr(o.side, "value", str(o.side)),
                    "order_type": getattr(o.order_type, "value", str(o.order_type)),
                    "quantity": o.quantity,
                    "price": o.price,
                    "status": getattr(o.status, "value", str(o.status)),
                    "filled_quantity": o.filled_quantity,
                    "avg_fill_price": o.avg_fill_price,
                    "trading_mode": getattr(o.trading_mode, "value", str(o.trading_mode)),
                    "placed_at": o.placed_at.replace(tzinfo=timezone.utc).isoformat() if o.placed_at else None,
                    "updated_at": iso,
                }
            )
        return items, last_ts


async def _fetch_positions(limit: int = 50) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(select(Position).order_by(desc(Position.updated_at)).limit(limit))
        ).scalars().all()
        items: List[Dict[str, Any]] = []
        last_ts: Optional[str] = None
        for p in rows:
            ts = p.updated_at or p.opened_at
            iso = ts.replace(tzinfo=timezone.utc).isoformat() if ts else None
            if iso and (last_ts is None or iso > last_ts):
                last_ts = iso
            items.append(
                {
                    "id": p.id,
                    "symbol": p.symbol,
                    "exchange": p.exchange,
                    "side": getattr(p.side, "value", str(p.side)),
                    "quantity": p.quantity,
                    "avg_price": p.avg_price,
                    "current_price": p.current_price,
                    "unrealized_pnl": p.unrealized_pnl,
                    "realized_pnl": p.realized_pnl,
                    "is_open": p.is_open,
                    "trading_mode": getattr(p.trading_mode, "value", str(p.trading_mode)),
                    "opened_at": p.opened_at.replace(tzinfo=timezone.utc).isoformat() if p.opened_at else None,
                    "updated_at": iso,
                }
            )
        return items, last_ts


async def _fetch_alerts(limit: int = 50) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(select(Alert).order_by(desc(Alert.created_at)).limit(limit))
        ).scalars().all()
        items: List[Dict[str, Any]] = []
        last_ts: Optional[str] = None
        for a in rows:
            iso = a.created_at.replace(tzinfo=timezone.utc).isoformat() if a.created_at else None
            if iso and (last_ts is None or iso > last_ts):
                last_ts = iso
            items.append(
                {
                    "id": a.id,
                    "title": a.title,
                    "message": a.message,
                    "level": getattr(a.level, "value", str(a.level)),
                    "source": a.source,
                    "is_read": a.is_read,
                    "created_at": iso,
                }
            )
        return items, last_ts


async def _fetch_portfolio() -> Tuple[Dict[str, Any], Optional[str]]:
    async with AsyncSessionLocal() as session:
        snap = (
            await session.execute(select(PortfolioSnapshot).order_by(desc(PortfolioSnapshot.date)).limit(1))
        ).scalars().first()
        if not snap:
            return {"latest": None}, None
        iso = snap.date.replace(tzinfo=timezone.utc).isoformat() if snap.date else None
        return (
            {
                "latest": {
                    "date": iso,
                    "total_value": snap.total_value,
                    "cash": snap.cash,
                    "positions_value": snap.positions_value,
                    "daily_pnl": snap.daily_pnl,
                    "total_pnl": snap.total_pnl,
                    "trading_mode": getattr(snap.trading_mode, "value", str(snap.trading_mode)),
                }
            },
            iso,
        )


@router.websocket("/ws/stream")
async def unified_stream(websocket: WebSocket) -> None:
    """
    Unified real-time stream.
    Client sends: {"action":"subscribe","topics":["orders","positions","alerts","portfolio"]}
    Server sends: {"type":"snapshot","topic":..., "data":..., "timestamp":...}
    """
    await websocket.accept()
    topics: Set[str] = set()
    last_sent_hash: Dict[str, int] = {}

    async def send_topic(topic: str) -> None:
        if topic == "orders":
            data, last_ts = await _fetch_orders()
            payload = {"items": data, "last_updated": last_ts}
        elif topic == "positions":
            data, last_ts = await _fetch_positions()
            payload = {"items": data, "last_updated": last_ts}
        elif topic == "alerts":
            data, last_ts = await _fetch_alerts()
            payload = {"items": data, "last_updated": last_ts}
        elif topic == "portfolio":
            data, last_ts = await _fetch_portfolio()
            payload = {**data, "last_updated": last_ts}
        else:
            return

        h = hash(json.dumps(payload, sort_keys=True, default=str))
        if last_sent_hash.get(topic) == h:
            return
        last_sent_hash[topic] = h
        await websocket.send_json({"type": "snapshot", "topic": topic, "data": payload, "timestamp": _now_iso()})

    try:
        while True:
            # Non-blocking receive so we can also push periodic snapshots.
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                msg = json.loads(raw)
                if msg.get("action") == "subscribe":
                    topics = {str(t).lower() for t in (msg.get("topics") or [])}
                    # Send immediately on subscribe.
                    for t in sorted(topics):
                        await send_topic(t)
                elif msg.get("action") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": _now_iso()})
            except TimeoutError:
                pass
            except json.JSONDecodeError:
                # ignore garbage
                pass

            for t in sorted(topics):
                await send_topic(t)
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        return
