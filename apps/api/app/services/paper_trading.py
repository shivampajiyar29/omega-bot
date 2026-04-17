"""
Paper Trading Engine
====================
* Reads AI signals from Redis (set by market_stream or bot loop)
* Executes BUY/SELL at latest live price (Binance for crypto, simulated for Indian)
* Updates Orders, Fills, Positions in PostgreSQL in real time
* Portfolio P&L is always mark-to-market against live prices
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import (
    BrokerConnector, ConnectorStatus, Fill, MarketType,
    Order, OrderSide, OrderStatus, OrderType,
    Position, TradingMode,
)
from app.services import market_stream

logger = logging.getLogger(__name__)

AI_SIGNAL_KEY_FMT = "omegabot:paper:signal:{symbol}"
LAST_ACTION_KEY   = "omegabot:paper:last_action:{symbol}"
LOCK_KEY          = "omegabot:paper:lock:{symbol}"

INITIAL_CAPITAL   = 1_000_000.0   # ₹10 lakh paper trading capital
DEFAULT_QTY_FRAC  = 0.02           # 2% of capital per trade


def _get_redis() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def _market_type(symbol: str) -> MarketType:
    s = symbol.upper()
    if s.endswith("USDT") or s.endswith("BUSD") or "BTC" in s or "ETH" in s:
        return MarketType.CRYPTO
    return MarketType.EQUITY


async def _get_or_create_connector(session: AsyncSession) -> str:
    result = await session.execute(
        select(BrokerConnector).where(BrokerConnector.is_default.is_(True)).limit(1)
    )
    row = result.scalar_one_or_none()
    if row:
        return row.id

    result2 = await session.execute(
        select(BrokerConnector).where(BrokerConnector.name == "mock").limit(1)
    )
    row2 = result2.scalar_one_or_none()
    if row2:
        return row2.id

    c = BrokerConnector(
        id=str(uuid.uuid4()), name="mock", display_name="Paper Trading",
        adapter_class="app.adapters.broker.mock_broker.MockBrokerAdapter",
        enabled=True, is_default=True, status=ConnectorStatus.CONNECTED,
        trading_mode=TradingMode.PAPER, market_types=["equity", "crypto"],
    )
    session.add(c)
    await session.flush()
    return c.id


async def place_paper_order(
    symbol: str, side: str, quantity: float, price: float,
    bot_id: Optional[str] = None,
) -> Optional[Order]:
    """
    Place and immediately fill a paper order.
    Returns the filled Order or None on error.
    """
    async with AsyncSessionLocal() as session:
        try:
            cid  = await _get_or_create_connector(session)
            side_e = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

            # For SELL: check we have a position
            if side_e == OrderSide.SELL:
                res = await session.execute(
                    select(Position).where(
                        Position.symbol == symbol.upper(),
                        Position.is_open.is_(True),
                        Position.side == OrderSide.BUY,
                        Position.trading_mode == TradingMode.PAPER,
                        Position.connector_id == cid,
                    )
                )
                pos = res.scalar_one_or_none()
                if not pos or float(pos.quantity) < quantity * 0.99:
                    logger.info("SELL skipped — no long position for %s", symbol)
                    return None

            order = Order(
                id=str(uuid.uuid4()), bot_id=bot_id, connector_id=cid,
                broker_order_id=f"paper-{uuid.uuid4().hex[:8]}",
                symbol=symbol.upper(), exchange="PAPER" if not symbol.upper().endswith("USDT") else "BINANCE",
                market_type=_market_type(symbol),
                side=side_e, order_type=OrderType.MARKET,
                quantity=quantity, price=price,
                status=OrderStatus.FILLED,
                filled_quantity=quantity, avg_fill_price=price,
                trading_mode=TradingMode.PAPER,
                tags={"source": "paper_ai", "automated": True},
                placed_at=datetime.now(timezone.utc),
            )
            session.add(order)

            fill = Fill(
                id=str(uuid.uuid4()), order_id=order.id,
                quantity=quantity, price=price, commission=0.0,
                filled_at=datetime.now(timezone.utc),
            )
            session.add(fill)

            await _update_position(session, order, price, quantity, cid)
            await session.commit()
            await session.refresh(order)

            logger.info("📋 Paper order FILLED: %s %s %.4f %s @ %.4f",
                        side.upper(), quantity, symbol, "PAPER", price)
            return order

        except Exception as e:
            await session.rollback()
            logger.error("place_paper_order failed: %s", e)
            return None


async def _update_position(
    session: AsyncSession, order: Order, price: float, qty: float, cid: str
) -> None:
    sym  = order.symbol
    mode = TradingMode.PAPER

    if order.side == OrderSide.BUY:
        res = await session.execute(
            select(Position).where(
                Position.symbol == sym, Position.connector_id == cid,
                Position.is_open.is_(True), Position.side == OrderSide.BUY,
                Position.trading_mode == mode,
            )
        )
        pos = res.scalar_one_or_none()
        if pos is None:
            pos = Position(
                id=str(uuid.uuid4()), symbol=sym, exchange=order.exchange,
                market_type=order.market_type, side=OrderSide.BUY,
                quantity=qty, avg_price=price, current_price=price,
                unrealized_pnl=0.0, realized_pnl=0.0,
                is_open=True, trading_mode=mode, connector_id=cid,
                opened_at=datetime.now(timezone.utc),
            )
            session.add(pos)
        else:
            nq = float(pos.quantity) + qty
            pos.avg_price      = (float(pos.quantity) * float(pos.avg_price) + qty * price) / nq
            pos.quantity       = nq
            pos.current_price  = price
            pos.unrealized_pnl = (price - pos.avg_price) * nq
            pos.updated_at     = datetime.now(timezone.utc)

    else:  # SELL
        res = await session.execute(
            select(Position).where(
                Position.symbol == sym, Position.connector_id == cid,
                Position.is_open.is_(True), Position.side == OrderSide.BUY,
                Position.trading_mode == mode,
            )
        )
        pos = res.scalar_one_or_none()
        if not pos:
            return
        close_qty = min(qty, float(pos.quantity))
        pnl       = (price - float(pos.avg_price)) * close_qty
        pos.realized_pnl  = float(pos.realized_pnl or 0) + pnl
        pos.quantity      = float(pos.quantity) - close_qty
        pos.current_price = price
        if pos.quantity <= 1e-6:
            pos.quantity = 0.0
            pos.is_open  = False
            pos.closed_at = datetime.now(timezone.utc)
        else:
            pos.unrealized_pnl = (price - float(pos.avg_price)) * pos.quantity
        pos.updated_at = datetime.now(timezone.utc)


async def execute_pending_signals_async() -> None:
    """
    Read AI signals from Redis → execute paper trades.
    Called by the bot loop and the Celery beat scheduler.
    """
    r = _get_redis()

    for sym in market_stream.DEFAULT_SYMBOLS:
        raw_sig = r.get(AI_SIGNAL_KEY_FMT.format(symbol=sym))
        if not raw_sig:
            continue
        try:
            sig: Dict[str, Any] = json.loads(raw_sig)
        except json.JSONDecodeError:
            continue

        action = str(sig.get("action", "hold")).lower()
        prev   = r.get(LAST_ACTION_KEY.format(symbol=sym))

        # Skip if action hasn't changed (avoid re-trading same signal)
        if prev == action:
            continue
        if action == "hold":
            r.set(LAST_ACTION_KEY.format(symbol=sym), "hold")
            continue

        # Lock to prevent concurrent execution for same symbol
        if not r.set(LOCK_KEY.format(symbol=sym), "1", nx=True, ex=10):
            continue

        try:
            tick  = market_stream.get_latest_price(sym)
            price = float(tick["price"]) if tick else 0.0
            if price <= 0:
                continue

            # Compute quantity: 2% of capital / current price
            quantity = max(1.0, round(INITIAL_CAPITAL * DEFAULT_QTY_FRAC / price, 4))
            if sym.endswith("USDT"):
                quantity = round(INITIAL_CAPITAL * DEFAULT_QTY_FRAC / price, 6)

            order = await place_paper_order(sym, action, quantity, price)
            if order:
                r.set(LAST_ACTION_KEY.format(symbol=sym), action)

        except Exception:
            logger.exception("execute_pending_signals failed for %s", sym)
        finally:
            r.delete(LOCK_KEY.format(symbol=sym))


async def mark_to_market_all() -> None:
    """Update all open position P&L against latest Redis prices."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Position).where(Position.is_open.is_(True))
        )
        for pos in result.scalars().all():
            tick = market_stream.get_latest_price(pos.symbol)
            if not tick:
                continue
            cur = float(tick["price"])
            pos.current_price  = cur
            pos.unrealized_pnl = (cur - float(pos.avg_price)) * float(pos.quantity)
            pos.updated_at     = datetime.now(timezone.utc)
        await session.commit()
