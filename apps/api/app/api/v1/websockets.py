"""
Real-Time WebSocket Endpoints
================================
/ws/market  — live price ticks (Binance for crypto, simulated for Indian)
/ws/bots    — bot status + P&L from DB
/ws/stream  — unified stream (orders, positions, alerts, portfolio)
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select, desc

from app.core.database import AsyncSessionLocal
from app.models.models import Order, Position, Alert, PortfolioSnapshot, Bot
from app.services import market_stream

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# /ws/market  — real-time price ticks
# Protocol:
#   Client → {"action":"subscribe","symbols":["BTCUSDT","RELIANCE"]}
#   Server → {"type":"tick","symbol":"BTCUSDT","price":87432.0,"exchange":"BINANCE","timestamp":"..."}
# ─────────────────────────────────────────────────────────────────────────────

@router.websocket("/ws/market")
async def market_feed(ws: WebSocket) -> None:
    await ws.accept()
    subscribed: List[str] = ["BTCUSDT", "ETHUSDT", "RELIANCE", "TCS"]

    try:
        while True:
            # Non-blocking receive for subscription changes
            try:
                raw = await asyncio.wait_for(ws.receive_text(), timeout=0.1)
                msg = json.loads(raw)
                if msg.get("action") == "subscribe" and msg.get("symbols"):
                    subscribed = [str(s).upper() for s in msg["symbols"]]
                elif msg.get("action") == "unsubscribe" and msg.get("symbols"):
                    remove = {str(s).upper() for s in msg["symbols"]}
                    subscribed = [s for s in subscribed if s not in remove]
                elif msg.get("action") == "ping":
                    await ws.send_json({"type": "pong", "timestamp": _now()})
            except (asyncio.TimeoutError, json.JSONDecodeError):
                pass

            # Send latest tick for each subscribed symbol
            for sym in subscribed:
                tick = market_stream.get_latest_price(sym)
                if tick:
                    # Attach AI signal if available
                    from app.services.market_stream import _get_redis, AI_SIGNAL_KEY_FMT
                    try:
                        raw_sig = _get_redis().get(AI_SIGNAL_KEY_FMT.format(symbol=sym))
                        signal_data = json.loads(raw_sig) if raw_sig else None
                    except Exception:
                        signal_data = None

                    await ws.send_json({
                        "type":      "tick",
                        "symbol":    tick["symbol"],
                        "price":     tick["price"],
                        "exchange":  tick.get("exchange", "UNKNOWN"),
                        "timestamp": tick.get("timestamp", _now()),
                        "ai_signal": signal_data,
                    })

            await asyncio.sleep(1.0)

    except WebSocketDisconnect:
        logger.debug("market_feed client disconnected")
    except Exception as e:
        logger.warning("market_feed error: %s", e)


# ─────────────────────────────────────────────────────────────────────────────
# /ws/bots  — live bot status + P&L from database
# ─────────────────────────────────────────────────────────────────────────────

@router.websocket("/ws/bots")
async def bot_feed(ws: WebSocket) -> None:
    await ws.accept()
    try:
        while True:
            async with AsyncSessionLocal() as db:
                rows = (await db.execute(select(Bot))).scalars().all()
                bots = []
                for b in rows:
                    bots.append({
                        "id":         b.id,
                        "name":       b.name,
                        "symbol":     b.symbol,
                        "exchange":   b.exchange,
                        "status":     getattr(b.status, "value", str(b.status)),
                        "trading_mode": getattr(b.trading_mode, "value", str(b.trading_mode)),
                        "started_at": b.started_at.isoformat() if b.started_at else None,
                    })

            await ws.send_json({
                "type":      "bot_update",
                "bots":      bots,
                "timestamp": _now(),
            })
            await asyncio.sleep(2.0)

    except WebSocketDisconnect:
        logger.debug("bot_feed client disconnected")
    except Exception as e:
        logger.warning("bot_feed error: %s", e)


# ─────────────────────────────────────────────────────────────────────────────
# /ws/stream  — unified real-time stream (orders, positions, alerts, portfolio)
# Protocol:
#   Client → {"action":"subscribe","topics":["orders","positions","alerts","portfolio"]}
#   Server → {"type":"snapshot","topic":"positions","data":{...},"timestamp":"..."}
# ─────────────────────────────────────────────────────────────────────────────

async def _fetch_orders(limit: int = 50) -> Tuple[List[Dict], Optional[str]]:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(Order).order_by(desc(Order.placed_at)).limit(limit)
        )).scalars().all()
        items, last_ts = [], None
        for o in rows:
            ts = (o.updated_at or o.placed_at)
            iso = ts.replace(tzinfo=timezone.utc).isoformat() if ts else None
            if iso and (last_ts is None or iso > last_ts):
                last_ts = iso
            items.append({
                "id":             o.id,
                "symbol":         o.symbol,
                "exchange":       o.exchange,
                "side":           getattr(o.side, "value", str(o.side)),
                "order_type":     getattr(o.order_type, "value", str(o.order_type)),
                "quantity":       o.quantity,
                "price":          o.price,
                "status":         getattr(o.status, "value", str(o.status)),
                "filled_quantity":o.filled_quantity,
                "avg_fill_price": o.avg_fill_price,
                "trading_mode":   getattr(o.trading_mode, "value", str(o.trading_mode)),
                "placed_at":      o.placed_at.replace(tzinfo=timezone.utc).isoformat() if o.placed_at else None,
            })
        return items, last_ts


async def _fetch_positions(limit: int = 50) -> Tuple[List[Dict], Optional[str]]:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(Position).order_by(desc(Position.updated_at)).limit(limit)
        )).scalars().all()
        items, last_ts = [], None
        for p in rows:
            # Mark-to-market with latest price
            tick = market_stream.get_latest_price(p.symbol)
            cur_price = float(tick["price"]) if tick else float(p.current_price or p.avg_price)
            if p.is_open:
                p.current_price  = cur_price
                p.unrealized_pnl = (cur_price - float(p.avg_price)) * float(p.quantity)

            ts  = p.updated_at or p.opened_at
            iso = ts.replace(tzinfo=timezone.utc).isoformat() if ts else None
            if iso and (last_ts is None or iso > last_ts):
                last_ts = iso
            items.append({
                "id":             p.id,
                "symbol":         p.symbol,
                "exchange":       p.exchange,
                "side":           getattr(p.side, "value", str(p.side)),
                "quantity":       p.quantity,
                "avg_price":      p.avg_price,
                "current_price":  cur_price,
                "unrealized_pnl": round(float(p.unrealized_pnl or 0), 2),
                "realized_pnl":   round(float(p.realized_pnl  or 0), 2),
                "is_open":        p.is_open,
                "trading_mode":   getattr(p.trading_mode, "value", str(p.trading_mode)),
                "opened_at":      p.opened_at.replace(tzinfo=timezone.utc).isoformat() if p.opened_at else None,
            })
        return items, last_ts


async def _fetch_alerts(limit: int = 50) -> Tuple[List[Dict], Optional[str]]:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(Alert).order_by(desc(Alert.created_at)).limit(limit)
        )).scalars().all()
        items, last_ts = [], None
        for a in rows:
            iso = a.created_at.replace(tzinfo=timezone.utc).isoformat() if a.created_at else None
            if iso and (last_ts is None or iso > last_ts):
                last_ts = iso
            items.append({
                "id": a.id, "title": a.title, "message": a.message,
                "level": getattr(a.level, "value", str(a.level)),
                "source": a.source, "is_read": a.is_read, "created_at": iso,
            })
        return items, last_ts


async def _fetch_portfolio() -> Tuple[Dict, Optional[str]]:
    async with AsyncSessionLocal() as db:
        # Compute live portfolio from open positions
        pos_rows = (await db.execute(
            select(Position).where(Position.is_open)
        )).scalars().all()

        positions_value = 0.0
        total_unrealized = 0.0
        for p in pos_rows:
            tick = market_stream.get_latest_price(p.symbol)
            cur  = float(tick["price"]) if tick else float(p.current_price or p.avg_price)
            val  = cur * float(p.quantity)
            positions_value  += val
            total_unrealized += (cur - float(p.avg_price)) * float(p.quantity)

        snap = (await db.execute(
            select(PortfolioSnapshot).order_by(desc(PortfolioSnapshot.date)).limit(1)
        )).scalars().first()

        cash = float(snap.cash) if snap else 1_000_000.0
        total_value = cash + positions_value

        return {
            "cash":            round(cash, 2),
            "positions_value": round(positions_value, 2),
            "total_value":     round(total_value, 2),
            "unrealized_pnl":  round(total_unrealized, 2),
            "realized_pnl":    round(float(snap.total_pnl or 0), 2) if snap else 0.0,
            "open_positions":  len(pos_rows),
        }, _now()


@router.websocket("/ws/stream")
async def unified_stream(ws: WebSocket) -> None:
    await ws.accept()
    topics: Set[str]          = set()
    last_hash: Dict[str, int] = {}

    async def push(topic: str) -> None:
        if topic == "orders":
            data, ts = await _fetch_orders()
            payload  = {"items": data, "last_updated": ts}
        elif topic == "positions":
            data, ts = await _fetch_positions()
            payload  = {"items": data, "last_updated": ts}
        elif topic == "alerts":
            data, ts = await _fetch_alerts()
            payload  = {"items": data, "last_updated": ts}
        elif topic == "portfolio":
            data, ts = await _fetch_portfolio()
            payload  = {**data, "last_updated": ts}
        else:
            return

        h = hash(json.dumps(payload, sort_keys=True, default=str))
        if last_hash.get(topic) == h:
            return
        last_hash[topic] = h
        await ws.send_json({
            "type": "snapshot", "topic": topic,
            "data": payload, "timestamp": _now(),
        })

    try:
        while True:
            try:
                raw = await asyncio.wait_for(ws.receive_text(), timeout=1.0)
                msg = json.loads(raw)
                if msg.get("action") == "subscribe":
                    topics = {str(t).lower() for t in (msg.get("topics") or [])}
                    for t in sorted(topics):
                        await push(t)
                elif msg.get("action") == "ping":
                    await ws.send_json({"type": "pong", "timestamp": _now()})
            except (asyncio.TimeoutError, json.JSONDecodeError):
                pass

            for t in sorted(topics):
                await push(t)
            await asyncio.sleep(1.0)

    except WebSocketDisconnect:
        logger.debug("unified_stream disconnected")
    except Exception as e:
        logger.warning("unified_stream error: %s", e)
